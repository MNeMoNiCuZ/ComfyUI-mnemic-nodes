# Workflow folders

Enhances ComfyUI's native **Workflows** sidebar with folder management. Workflows
remain ordinary files in the active user's `workflows` directory. The extension
does not replace the sidebar or modify the ComfyUI installation.

Restart ComfyUI after installing/updating this feature, then refresh the browser.
Open **Workflows** in the left sidebar.

## Controls

- The **folder-plus icon** at the right end of the **Browse** row creates a
  folder. Choose its parent to create a subfolder. There is no extra toolbar row.
- **Right-click a folder**, or click its vertical **⋮** button, for **New subfolder**,
  **Rename folder**, **Move folder to…**, **Open folder**, and **Copy folder path**.
  Every folder's menu button stays visible, including folders created outside ComfyUI.
- **Open folder** opens the real directory in Explorer, Finder, or the Linux
  desktop file manager. It is available when connecting through loopback on the
  ComfyUI machine. **Copy folder path** also works remotely and copies the
  resolved absolute path, including the target of a directory link.
- **Right-click Browse or the empty root background** for root folder actions.
- **Drag workflows or folders onto a folder** to move them into it. Drop onto the
  **Browse** row or empty tree background to move an item back to the root. Drop
  feedback appears only while dragging; there is no dedicated drop strip.
- **Right-click a workflow → Rename** uses ComfyUI's existing workflow rename action.
- The native **Refresh** button re-reads workflows and folders from disk. Use it
  after creating, moving, or renaming folders in your system's file manager.
  It fetches folders directly without browser caching, including empty root folders.
  Empty directories appear alongside the native workflow tree and can be expanded.

Folder drag/drop and folder actions apply to the **Browse** section. Native
workflow loading, search, bookmarks, and workflow-to-canvas dragging remain
available. The tree lists folders alphabetically before workflow files.

The tree includes ordinary folders and configured directory links/junctions,
including links to workflow libraries on other drives. It follows linked
directories without recursing through link cycles. Creating/moving files inside
a linked folder operates on its real storage. Renaming a linked folder moves
the link itself, keeping its target intact. Cross-drive moves of files and
ordinary folders use a copy/remove fallback; a junction itself can only be
moved within its own drive.

Moves preserve nested folders and other files inside the moved directory.
ComfyUI's workflow store updates affected tabs, drafts, bookmarks, and thumbnails
without reloading the graph, including workflows with unsaved edits. Name
collisions are rejected; there is no overwrite/merge option. A folder cannot be
moved inside itself. Case-only renames are rejected on Windows when the existing
destination name resolves to the same directory.

## Settings and compatibility

**Settings → ⚡MNeMiC Nodes → Workflow Folders → Enhance native workflow folders**
turns the enhancement on or off. This is a native ComfyUI setting registered in
the pack's shared `web/js/settings.js`, and ComfyUI saves the preference for the
active user. It is enabled by default. Disabling it immediately removes the
added controls and stops their observers and workflow subscriptions. No restart
is needed to toggle it; directories and saved workflows remain on disk.

The sidebar integration was checked against the installed ComfyUI frontend
**1.53.6**. ComfyUI exposes its workflow state API, but has no public hook for
extending these folder rows. This extension attaches scoped DOM controls using
the sidebar's existing classes and tree keys; frontend changes may require an
update to those selectors. It does not import hashed bundles or access Vue
component internals.

Backend paths resolve from ComfyUI's active user directory, including custom
`--user-directory` and multi-user setups. Operations accept only relative paths
in that user's workflow tree, including existing configured links to external
storage. Absolute paths and traversal components are rejected. Folder deletion
is not included.

The JavaScript state regression checks run with:

```powershell
node --test tests/workflow_folder_core.test.mjs
```

Browser checks used disk-derived directory listings and temporary in-memory
fixtures for creation, renaming, nesting, drag/drop, and disk refresh. The new
Python routes were reviewed by reading;
they were not run outside ComfyUI. After restarting, verify the folder operations
in ComfyUI with a disposable workflow before organizing a large collection.
