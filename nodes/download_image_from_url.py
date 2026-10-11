import os
import ntpath
import re
import stat
import tempfile
import socket
import ipaddress
import requests
from requests.adapters import HTTPAdapter
import torch
import numpy as np
from PIL import Image
from io import BytesIO
from urllib.parse import urljoin, urlparse

import folder_paths
from comfy_api.latest import io
from ..utils.date_templates import resolve_date_template


SAVE_LOCATIONS = {
    "input": folder_paths.get_input_directory,
    "output": folder_paths.get_output_directory,
}

SAVE_FORMATS = {"png": ("PNG", ".png"), "jpeg": ("JPEG", ".jpg"), "webp": ("WEBP", ".webp")}

NAT64 = ipaddress.ip_network('64:ff9b::/96')


def _validate_component(component):
    # Use the same strict rules on every OS. Windows trims trailing dots/spaces
    # and interprets colons as drive prefixes or alternate data streams.
    if (not component or component in ('.', '..') or component.endswith(('.', ' '))
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', component)
            or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?', component, re.IGNORECASE)):
        raise ValueError("Paths and names must contain ordinary folder/file names, without traversal or special path syntax.")


def _additive_components(path):
    if not path:
        return []
    if ntpath.isabs(path) or ntpath.splitdrive(path)[0]:
        raise ValueError("path must only add subfolders beneath the selected location.")
    components = path.replace('\\', '/').split('/')
    for component in components:
        _validate_component(component)
    return components


def _reject_link(path):
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return
    if (stat.S_ISLNK(info.st_mode)
            or getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)):
        raise ValueError("Saving through symlinks, junctions or other reparse points is not allowed.")


def _checked_save_paths(base_dir, components, filename=None):
    # base_dir is the trusted, canonical ComfyUI root. All user components have
    # already been validated; none are normalized or interpreted as traversal.
    save_dir = base_dir
    _reject_link(base_dir)
    for component in components:
        save_dir = os.path.join(save_dir, component)
        _reject_link(save_dir)
    file_path = os.path.join(save_dir, filename) if filename is not None else None
    if file_path is not None:
        _reject_link(file_path)
    for target in (save_dir, file_path):
        if target is None:
            continue
        resolved = os.path.realpath(target)
        try:
            contained = os.path.normcase(os.path.commonpath([base_dir, resolved])) == os.path.normcase(base_dir)
        except ValueError:
            contained = False
        if not contained:
            raise ValueError("The save path escapes the selected ComfyUI folder.")
    return save_dir, file_path


def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


def is_public(ip):
    # IPv6 forms that wrap an IPv4 address are judged by that address
    if ip.version == 6 and (ip.ipv4_mapped or ip.sixtofour or ip in NAT64):
        ip = ip.ipv4_mapped or ip.sixtofour or ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    return ip.is_global and not ip.is_multicast


def resolve_public(hostname, port):
    # Blocks localhost, the LAN and cloud metadata endpoints
    addresses = [ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)]
    if not all(is_public(ip) for ip in addresses):
        raise ValueError(f"Refusing to download from a local or private address: `{hostname}`")
    return addresses[0]


class PinnedAdapter(HTTPAdapter):
    # Connects to an address that was already checked, so a second DNS lookup can't swap in a private one.
    # HTTPS still sends and verifies the real hostname.
    def __init__(self, hostname):
        self.hostname = hostname
        super().__init__()

    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, server_hostname=self.hostname, assert_hostname=self.hostname, **kwargs)


def fetch(url):
    for _ in range(5):
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            raise ValueError(f"Only http and https image URLs are supported: `{url}`")
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        ip = resolve_public(parsed.hostname, port)
        host = f"[{ip}]" if ip.version == 6 else str(ip)
        with requests.Session() as session:
            session.trust_env = False  # A proxy would do its own unchecked DNS lookup
            if parsed.scheme == 'https':
                session.mount("https://", PinnedAdapter(parsed.hostname))
            response = session.get(
                parsed._replace(netloc=f"{host}:{port}").geturl(),
                headers={'Host': parsed.netloc.rpartition('@')[2]},
                timeout=30,
                allow_redirects=False,
            )
        if not response.is_redirect:
            return response
        url = urljoin(url, response.headers['Location'])
    raise ValueError("Too many redirects while downloading the image.")


class DownloadImageFromURL(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_DownloadImageFromURL",
            display_name="🖼️ Download Image from URL",
            category="⚡ MNeMiC Nodes",
            description="Downloads an image from a public URL, optionally saving it in ComfyUI's input or output folder.",
            inputs=[
                io.String.Input(
                    "image_url",
                    multiline=False,
                    default="",
                    placeholder="https://example.com/image.png",
                    tooltip="URL of the image to download.",
                ),
                io.Boolean.Input(
                    "save",
                    default=False,
                    tooltip="Keep a copy in input or output and show the save settings. When off, writes a temporary PNG in ComfyUI's temp folder.",
                ),
                io.String.Input(
                    "name",
                    default="%date:yyyy-MM-dd - hh.mm.ss%",
                    multiline=False,
                    placeholder="%date:yyyy-MM-dd - hh.mm.ss%",
                    tooltip="Filename prefix template. Defaults to a date and time, like Save Image With Metadata. Supports date and strftime tokens; empty uses the URL filename.",
                ),
                io.String.Input(
                    "path",
                    default="%date:yyyy-MM-dd%",
                    multiline=False,
                    placeholder="%date:yyyy-MM-dd%",
                    tooltip="Folder prefix template inside the save location. Defaults to a dated subfolder. Empty uses the selected folder; only additive subfolders are allowed.",
                ),
                io.Combo.Input(
                    "save_location",
                    options=list(SAVE_LOCATIONS),
                    default="input",
                    tooltip="ComfyUI folder to save in: input (default) or output.",
                ),
                io.Boolean.Input(
                    "overwrite",
                    default=False,
                    tooltip="Replace an existing file with the same name. When off, the existing file is kept and the image is only passed downstream.",
                ),
                io.Combo.Input(
                    "file_format",
                    options=list(SAVE_FORMATS),
                    default="png",
                    tooltip="File type to write. PNG is lossless; jpeg and webp use the quality setting.",
                ),
                io.Int.Input(
                    "quality",
                    default=100, min=1, max=100, advanced=True,
                    tooltip="Compression quality for jpeg and webp, 1-100. Ignored for PNG.",
                ),
            ],
            outputs=[
                io.Image.Output(display_name="image", tooltip="The downloaded image."),
                io.Int.Output(display_name="width", tooltip="The width of the image in pixels."),
                io.Int.Output(display_name="height", tooltip="The height of the image in pixels."),
            ],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, image_url, save=False, name="%date:yyyy-MM-dd - hh.mm.ss%", path="%date:yyyy-MM-dd%", save_location="input", overwrite=False, file_format="png", quality=100) -> io.NodeOutput:
        if not image_url:
            print("Error: No image URL provided.")
            return io.NodeOutput(None, None, None)

        url_path = urlparse(image_url).path
        file_extension = os.path.splitext(url_path)[1].lower()
        if file_extension not in ['.jpg', '.jpeg', '.png', '.webp']:
            print(f"Error: Unsupported image format `{file_extension}`")
            return io.NodeOutput(None, None, None)

        if save:
            if save_location not in SAVE_LOCATIONS:
                raise ValueError(f"Invalid save location `{save_location}`.")
            if file_format not in SAVE_FORMATS:
                raise ValueError(f"Invalid image format `{file_format}`.")
            if not 1 <= quality <= 100:
                raise ValueError("Quality must be between 1 and 100.")

            # Reject literal traversal before expansion, and validate the result
            # again so a date template cannot introduce special path syntax.
            _additive_components(re.sub(r'%date:[^%]+%', 'date', path))
            components = _additive_components(resolve_date_template(path))
            if name:
                _validate_component(re.sub(r'%date:[^%]+%', 'date', name))
                filename = resolve_date_template(name)
            else:
                filename = url_path.rsplit('/', 1)[-1]
            _validate_component(filename)
            # Only remove known image extensions; date templates often contain dots.
            stem, extension = os.path.splitext(filename)
            if extension.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
                filename = stem
            image_format, extension = SAVE_FORMATS[file_format]
            filename += extension
            _validate_component(filename)

            base_dir = os.path.realpath(SAVE_LOCATIONS[save_location]())
        else:
            # Hidden save settings never influence temporary paths or encoding.
            base_dir = os.path.realpath(folder_paths.get_temp_directory())
            components = []
            filename = None
            image_format, file_format, quality, overwrite = 'PNG', 'png', 100, False
        save_dir, file_path = _checked_save_paths(base_dir, components, filename)

        try:
            response = fetch(image_url)
            if response.status_code != 200:
                print(f"Error: Failed to fetch image from URL with status code {response.status_code}")
                return io.NodeOutput(None, None, None)

            image = Image.open(BytesIO(response.content)).convert('RGB')
            width, height = image.size

            os.makedirs(save_dir, exist_ok=True)
            save_dir, file_path = _checked_save_paths(base_dir, components, filename)
            options = {} if file_format == 'png' else {'quality': quality}
            if not save or overwrite:
                # An exclusive random file prevents a pre-existing temp symlink
                # from being followed. Replacing the final directory entry also
                # avoids modifying an outside file through an existing hardlink.
                fd, staging_path = tempfile.mkstemp(
                    prefix='mnemic-download-', suffix='.png' if not save else '.tmp', dir=save_dir,
                )
                try:
                    with os.fdopen(fd, 'wb') as f:
                        image.save(f, image_format, **options)
                    if save:
                        _, file_path = _checked_save_paths(base_dir, components, filename)
                        os.replace(staging_path, file_path)
                    staging_path = None  # The temp copy is kept, or was moved.
                finally:
                    if staging_path is not None:
                        os.unlink(staging_path)
            else:
                # Exclusive creation never follows or overwrites an existing file.
                try:
                    with open(file_path, 'xb') as f:
                        image.save(f, image_format, **options)
                except FileExistsError:
                    print(f"Skipped saving: `{file_path}` already exists and overwrite is off.")

            image_tensor = pil2tensor(image)

        except (requests.RequestException, OSError) as e:
            print(f"Error processing the image: {e}")
            return io.NodeOutput(None, None, None)

        return io.NodeOutput(image_tensor, width, height)
