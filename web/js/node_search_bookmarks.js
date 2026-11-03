import { app } from "../../../scripts/app.js";

// ComfyUI ranks node search results by how well the text matches and never
// looks at bookmarks. This moves bookmarked nodes to the top, keeping the
// match order within each group. Both search dialogs call the node definition
// store's nodeSearchService.searchNode, and the store rebuilds that service
// when node definitions change, so the patch goes on the service's class.
const SETTING = "MNeMiC.NodeSearch.BookmarksFirst";
const BOOKMARKS = "Comfy.NodeLibrary.Bookmarks.V2";

const setting = (id) => app.extensionManager?.setting?.get?.(id) ?? app.ui?.settings?.getSettingValue?.(id);

app.registerExtension({
    name: "MNeMiC.NodeSearchBookmarks",
    setup() {
        const pinia = document.getElementById("vue-app")?.__vue_app__?.config.globalProperties.$pinia;
        const service = pinia?._s.get("nodeDef")?.nodeSearchService;
        const proto = service && Object.getPrototypeOf(service);
        if (typeof proto?.searchNode !== "function") {
            console.warn("[MNeMiC] Bookmarks first in node search is unavailable: this ComfyUI frontend's node search was not found.");
            return;
        }
        if (proto.searchNode.mnemicBookmarksFirst) return;
        const searchNode = proto.searchNode;
        proto.searchNode = function (query, filters, options, ...rest) {
            if (setting(SETTING) === false) return searchNode.call(this, query, filters, options, ...rest);
            // Sort the full result list before the limit, so a bookmarked
            // match ranked below the cut still shows.
            const results = searchNode.call(this, query, filters, undefined, ...rest);
            const bookmarks = new Set(setting(BOOKMARKS) ?? []);
            const isBookmarked = (node) => bookmarks.has(node.name) || bookmarks.has(node.nodePath);
            const sorted = [...results.filter(isBookmarked), ...results.filter((node) => !isBookmarked(node))];
            return options?.limit ? sorted.slice(0, options.limit) : sorted;
        };
        proto.searchNode.mnemicBookmarksFirst = true;
    },
});
