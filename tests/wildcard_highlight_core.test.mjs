// Run with: node --test tests/
import { test } from "node:test";
import assert from "node:assert/strict";
import { parseWildcardText, renderWildcardHTML } from "../web/js/wildcard_highlight_core.js";

function types(node, out = []) {
    for (const child of node.children) {
        out.push(child.type);
        types(child, out);
    }
    return out;
}

test("nested blocks, variables and wildcards are recognized", () => {
    const found = types(parseWildcardText("${a=!{x|{y|z}}} a ${a} __colors__ <lora:l:1>"));
    for (const type of ["vardef", "varname", "choice", "option", "varuse", "wildcard", "tag"]) {
        assert.ok(found.includes(type), `missing ${type}`);
    }
    assert.equal(found.filter((t) => t === "choice").length, 2);
});

test("a variable's definition and uses share a color", () => {
    const html = renderWildcardHTML("${animal=!cat} A ${animal} and ${animal}.");
    const colors = [...html.matchAll(/class="mnm-wh-var(?:def|use)" style="background-color:([^;]+)/g)].map((m) => m[1]);
    assert.equal(colors.length, 3);
    assert.equal(new Set(colors).size, 1);
});

test("unclosed blocks only flag their opening characters", () => {
    const root = parseWildcardText("{oops then {a|b}");
    assert.equal(root.children[0].type, "error");
    assert.equal(root.children[0].end, 1);
    assert.equal(root.children[1].type, "choice");
});

test("rendering keeps the text unchanged", () => {
    const text = "${v=!{a|b}} <x:1> {2-3$$, $$p|5::q #c\n} } {z";
    const html = renderWildcardHTML(text);
    const plain = html.replace(/<[^>]*>/g, "").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&amp;/g, "&");
    assert.equal(plain, text);
});

test("many nested unclosed blocks parse quickly", () => {
    for (const unit of ["{", "${a=!"]) {
        const start = performance.now();
        parseWildcardText(unit.repeat(200));
        assert.ok(performance.now() - start < 500, `${unit} x200 took too long`);
    }
});
