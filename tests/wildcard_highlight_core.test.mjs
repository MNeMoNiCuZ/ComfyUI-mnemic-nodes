// Run with: node --test tests/
import { test } from "node:test";
import assert from "node:assert/strict";
import { computeWildcardRanges, parseWildcardText, renderWildcardHTML } from "../web/js/wildcard_highlight_core.js";

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

test("a block inside a # comment does not end the comment", () => {
    const root = parseWildcardText("{red\n|# {dark|light} blue\n|green}");
    assert.equal(root.children.length, 1);
    assert.equal(root.children[0].type, "choice");
    assert.ok(!types(root).includes("error"));
});

test("counts and weights after a line break are recognized", () => {
    const kinds = [];
    const collect = (node) => {
        if (node.type === "delim") kinds.push(node.kind);
        node.children.forEach(collect);
    };
    collect(parseWildcardText("{\n2$$a|b|c} {\n5::a\n|1::b\n}"));
    assert.ok(kinds.includes("count"));
    assert.equal(kinds.filter((k) => k === "weight").length, 2);
});

test("variables used inside a variable definition are flagged", () => {
    const root = parseWildcardText("${a=!cat} ${b=!big ${a}} ${b}");
    const uses = [];
    const collect = (node) => {
        if (node.type === "varuse") uses.push(node);
        node.children.forEach(collect);
    };
    collect(root);
    assert.equal(uses.length, 2);
    assert.ok(uses[0].error, "use inside a definition should be flagged");
    assert.ok(!uses[1].error, "top-level use should be fine");
});

test("custom colors accept hex and rgb()", () => {
    const html = renderWildcardHTML("{a|b}", { palette: "Custom", customColors: "rgb(255, 0, 0), #00ff00" });
    assert.ok(html.includes("rgba(255,0,0,"));
});

test("pathological text renders plainly instead of crashing or stalling", () => {
    const inputs = [
        "{".repeat(3000) + "}".repeat(3000),
        "${a=!".repeat(4000),
        "{".repeat(2000) + "a".repeat(18000),
        "{#".repeat(5000),
        "{1$$".repeat(8000),
    ];
    for (const text of inputs) {
        const start = performance.now();
        const html = renderWildcardHTML(text);
        assert.ok(performance.now() - start < 300, `took too long for length ${text.length}`);
        assert.ok(html.startsWith(text.slice(0, 20).replace(/&/g, "&amp;").replace(/</g, "&lt;")));
    }
});

function collect(node, type, out = []) {
    for (const child of node.children) {
        if (child.type === type) out.push(child);
        collect(child, type, out);
    }
    return out;
}

test("wildcard syntax inside tags is parsed", () => {
    const root = parseWildcardText("${l=!{a|b}} photo <lora:{styleA|styleB}:0.8> <lora:${l}:1> <lora:${x}:1>");
    const tags = collect(root, "tag");
    assert.equal(tags.length, 3);
    assert.equal(collect(tags[0], "choice").length, 1);
    const uses = collect(root, "varuse");
    assert.ok(!uses[0].error, "defined variable in a tag");
    assert.ok(uses[1].error, "undefined variable in a tag");
});

test("tags do not nest into each other", () => {
    const root = parseWildcardText("<a:{x|y} ".repeat(2500));
    assert.ok(!root.tooComplex);
});

test("an unbalanced definition ends at the first } like the processor", () => {
    const root = parseWildcardText("${hair=!{red|blond} a girl with ${hair} hair");
    const [def] = collect(root, "vardef");
    assert.equal(def.end, "${hair=!{red|blond}".length);
    assert.ok(def.error);
    assert.equal(collect(root, "choice").length, 0);
    const [use] = collect(root, "varuse");
    assert.ok(!use.error, "the processor still defines the variable");
});

test("each definition's value is its own variable scope", () => {
    const inner = parseWildcardText("${a=!${b=!x} ${b}} A=[${a}]");
    const innerUses = collect(inner, "varuse");
    assert.ok(innerUses.every((u) => !u.error));

    const outer = parseWildcardText("${a=!${b=!x}} B=[${b}]");
    const [use] = collect(outer, "varuse");
    assert.ok(use.error, "b is only defined inside a's value");
});

test("highlight ranges cover the styled text", () => {
    const ranges = computeWildcardRanges("a {red|blue} ${v=!x} ${v}");
    assert.ok(ranges.length > 0);
    for (const r of ranges) {
        assert.ok(r.end > r.start && r.css && r.layer >= 1);
    }
    const block = ranges.find((r) => r.start === 2 && r.end === 12);
    assert.ok(block, "the {red|blue} block is one range");
});
