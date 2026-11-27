#!/usr/bin/env python3
"""Check the Laravel symbols the package names against a pinned laravel/framework source.

Subcommands:
  index SRC_DIR [--tag T] [--out FILE]
        write the index (default scripts/data/laravel-source-index.tsv, and the tag to
        scripts/data/laravel-source-tag.txt) from a laravel/framework checkout: its
        src/Illuminate/ and config/ directories are read
  check [PATHS...]
        check every Laravel symbol named in the given files or directories (default:
        resources/boost/skills and agents) against the index. Exit 1 on a symbol that
        does not exist, 0 when all resolve, 2 on a usage or data error.

What `check` looks at in each markdown file:
  - fully qualified Illuminate\\... names anywhere in the file, and Illuminate\\...::member
  - `use Illuminate\\...;` lines (group syntax included)
  - Short::member in inline code and fenced code, where Short is imported in the block,
    a default facade alias (DB, Cache, Route, Str, ...), or a unique Illuminate short name
  - artisan commands: `php artisan <cmd>`, `artisan <cmd>` and Artisan::call('<cmd>')
  - config('file.key') and Config::get('file.key'): the top-level key, for the config
    files laravel/framework ships (services.php is app-owned and skipped; deeper keys
    such as database.connections.<name> are app-defined and not checked)

Facades resolve through their docblocks: Laravel maintains an `@method static` line for
every method a facade forwards to its root, so a facade's members are its @method lines,
its own static methods and the methods of Illuminate\\Support\\Facades\\Facade. Nothing
else: DB::transaction resolves, DB::transactional does not.

Only provable misses fail. A member is provably missing when it is absent from the class,
its parents, traits and @mixin classes, and the chain neither leaves Illuminate (a Symfony
or PHP parent) nor defines __call/__callStatic itself. The Macroable trait's magic methods
do not count: macros are app code, not framework symbols. Deliberate mentions of names
that are not in laravel/framework go in scripts/data/symbol-allow.tsv with a reason.

Python 3.9+, standard library only. No network.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "scripts" / "data"
INDEX_TSV = DATA / "laravel-source-index.tsv"
TAG_TXT = DATA / "laravel-source-tag.txt"
ALLOW_TSV = DATA / "symbol-allow.tsv"
DEFAULT_TARGETS = ["resources/boost/skills", "agents"]

IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
QNAME = rf"\\?{IDENT}(?:\\{IDENT})*"

FACADE_BASE = "Illuminate\\Support\\Facades\\Facade"
MACROABLE = "Illuminate\\Support\\Traits\\Macroable"
MAGIC = {"__call", "__callstatic"}
UNIVERSAL_MEMBERS = {"class", "__construct", "__tostring", "__get", "__set", "__isset", "__unset",
                     "__call", "__callstatic", "__invoke", "__serialize", "__unserialize"}
# Commands every artisan binary has: Symfony Console's built-ins.
SYMFONY_COMMANDS = ("completion", "help", "list")
# config/services.php exists to hold third-party keys an app adds.
APP_OWNED_CONFIG = {"services"}


class UsageError(Exception):
    pass


# ----------------------------------------------------------------------------
# index
# ----------------------------------------------------------------------------

def strip_php_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)
    return re.sub(r"(?m)(?<![:\"'\\])//[^\n]*|^\s*#(?!\[)[^\n]*", "", src)


def resolve(name: str, ns: str, uses: dict[str, str]) -> str:
    name = name.strip()
    if name.startswith("\\"):
        return name[1:]
    head, _, rest = name.partition("\\")
    if head in uses:
        return uses[head] + ("\\" + rest if rest else "")
    return f"{ns}\\{name}" if ns else name


def split_names(text: str) -> list[str]:
    return [p for p in re.split(r"\s*,\s*", text.strip()) if p]


def docblock_method(line: str) -> str | None:
    """Method name of an `@method [static] [type] name(...)` docblock line.

    The return type may hold spaces, generics and callable signatures
    (`\\Illuminate\\Support\\Collection<int, mixed>`), so the name is the first
    `ident(` whose preceding text has balanced brackets.
    """
    m = re.search(r"@method\s+(?:static\s+)?(.*)$", line)
    if not m:
        return None
    rest = m.group(1)
    for cand in re.finditer(rf"({IDENT})\s*\(", rest):
        before = rest[:cand.start()]
        if all(before.count(a) == before.count(b) for a, b in ("<>", "{}", "()", "[]")):
            if before and not before[-1].isspace():
                continue
            return cand.group(1)
    return None


def parse_php(path: Path) -> list[tuple]:
    """Index rows for one PHP file."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    src = strip_php_comments(raw)
    m = re.search(rf"^\s*namespace\s+({QNAME})\s*;", src, re.M)
    ns = m.group(1) if m else ""
    uses: dict[str, str] = {}
    for um in re.finditer(rf"^use\s+({QNAME})(?:\s+as\s+({IDENT}))?\s*;", src, re.M):
        full = um.group(1).lstrip("\\")
        uses[um.group(2) or full.rsplit("\\", 1)[-1]] = full

    decl = re.search(
        rf"^\s*(?:(?:abstract|final|readonly)\s+)*(class|interface|trait|enum)\s+({IDENT})"
        rf"(?:\s*:\s*{IDENT})?([^{{]*)\{{",
        src, re.M,
    )
    if not decl:
        # Namespaced functions (Illuminate\Support\enum_value, ...).
        rows = []
        if ns:
            # Top level, or one level in, inside an `if (! function_exists(...))` guard.
            for fm in re.finditer(rf"^(?:    )?function\s+&?({IDENT})\s*\(", src, re.M):
                rows.append(("function", f"{ns}\\{fm.group(1)}", "", ""))
        return rows
    kind, short, header = decl.group(1), decl.group(2), decl.group(3)
    fqcn = f"{ns}\\{short}" if ns else short
    extends: list[str] = []
    implements: list[str] = []
    em = re.search(rf"\bextends\s+((?:{QNAME}\s*,?\s*)+?)(?=\bimplements\b|$)", header)
    if em:
        extends = [resolve(p, ns, uses) for p in split_names(em.group(1))]
    im = re.search(rf"\bimplements\s+((?:{QNAME}\s*,?\s*)+)", header)
    if im:
        implements = [resolve(p, ns, uses) for p in split_names(im.group(1))]
    if kind == "interface":
        implements, extends = extends, []

    body = src[decl.end():]
    traits: list[str] = []
    for tm in re.finditer(rf"^\s*use\s+((?:{QNAME}\s*,\s*)*{QNAME})\s*[;{{]", body, re.M):
        traits += [resolve(t, ns, uses) for t in split_names(tm.group(1))]
    # @mixin applies to the class docblock (raw text before the declaration).
    head_raw = raw[:raw.find(decl.group(0).strip())] if decl.group(0).strip() in raw else raw
    mixins = [resolve(x, ns, uses) for x in re.findall(rf"@mixin\s+({QNAME})", head_raw)]

    rows = [("class", fqcn, kind, ",".join(extends), ",".join(implements), ",".join(traits), ",".join(mixins))]
    for fm in re.finditer(
        rf"^\s*((?:(?:public|protected|private|static|abstract|final)\s+)*)function\s+&?({IDENT})\s*\(",
        body, re.M,
    ):
        if "private" in fm.group(1).split() and fm.group(2).lower() not in MAGIC:
            continue
        rows.append(("method", fqcn, fm.group(2), ""))
    for cm in re.finditer(rf"^\s*(?:(?:public|protected|final)\s+)*const\s+(?:{IDENT}\s+)?({IDENT})\s*=", body, re.M):
        rows.append(("const", fqcn, cm.group(1), ""))
    if kind == "enum":
        for cm in re.finditer(rf"^\s*case\s+({IDENT})\s*[=;]", body, re.M):
            rows.append(("const", fqcn, cm.group(1), ""))
    for pm in re.finditer(
        rf"^\s*(?:public|protected)(?:\s+(?:static|readonly))*(?:\s+\??{QNAME}(?:\|{QNAME})*)?\s+\$({IDENT})",
        body, re.M,
    ):
        rows.append(("prop", fqcn, pm.group(1), ""))
    for line in head_raw.splitlines():
        if "@method" in line:
            name = docblock_method(line)
            if name:
                rows.append(("method", fqcn, name, "doc"))
        dm = re.search(rf"@property(?:-read|-write)?\s+.*?\$({IDENT})", line)
        if dm:
            rows.append(("prop", fqcn, dm.group(1), "doc"))

    if kind == "class" and FACADE_BASE in extends:
        acc = re.search(r"function\s+getFacadeAccessor\s*\(\s*\)[^{]*\{\s*return\s+([^;]+);", body)
        accessor = ""
        if acc:
            val = acc.group(1).strip()
            if re.fullmatch(r"'[^']*'|\"[^\"]*\"", val):
                accessor = val[1:-1]
            elif val.endswith("::class"):
                accessor = resolve(val[:-7], ns, uses)
            else:
                accessor = val
        sees = sorted({resolve(x, ns, uses) for x in re.findall(rf"@see\s+({QNAME})", head_raw)})
        rows.append(("facade", fqcn, accessor, ",".join(sees)))

    if fqcn == FACADE_BASE:
        am = re.search(r"function\s+defaultAliases\s*\(\s*\)(.*?)\n    }", body, re.S)
        if am:
            for alias, target in re.findall(rf"'({IDENT})'\s*=>\s*({QNAME})::class", am.group(1)):
                rows.append(("alias", alias, resolve(target, ns, uses), ""))

    for att in re.finditer(r"#\[AsCommand\((.*?)\)\]", src, re.S):
        args = att.group(1)
        nm = re.search(r"(?:name:\s*)?'([^']+)'", args)
        names = nm.group(1).split("|") if nm else []
        al = re.search(r"aliases:\s*\[([^\]]*)\]", args)
        if al:
            names += re.findall(r"'([^']+)'", al.group(1))
        for n in names:
            if n:
                rows.append(("command", n, fqcn, ""))
    return rows


def config_rows(config_dir: Path) -> list[tuple]:
    """(config, file, key) for the top-level keys of each framework config file."""
    rows = []
    tok = re.compile(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|=>|[\[\]\(\),]")
    for php in sorted(config_dir.glob("*.php")):
        src = strip_php_comments(php.read_text(encoding="utf-8", errors="replace"))
        start = src.find("return [")
        if start < 0:
            continue
        stack: list[str] = []  # open "[" and "(" brackets
        last_str: str | None = None
        for t in tok.findall(src[start + len("return "):]):
            if t[0] in "'\"":
                last_str = t[1:-1]
                continue
            if t == "=>" and last_str is not None and stack == ["["]:
                rows.append(("config", php.stem, last_str, ""))
            elif t in "[(":
                stack.append(t)
            elif t in ")]" and stack:
                stack.pop()
                if not stack:
                    break
            last_str = None
    return rows


def cmd_index(args) -> int:
    root = Path(args.src).resolve()
    src_dir = root / "src" / "Illuminate"
    if not src_dir.is_dir():
        print(f"{args.src}: no src/Illuminate directory (expected a laravel/framework checkout)", file=sys.stderr)
        return 2
    rows: list[tuple] = []
    files = [p for p in sorted(src_dir.rglob("*.php")) if "/stubs/" not in p.as_posix()]
    for php in files:
        rows += parse_php(php)
    if (root / "config").is_dir():
        rows += config_rows(root / "config")
    rows += [("command", c, "symfony/console", "") for c in SYMFONY_COMMANDS]
    rows = sorted(set(rows))
    tag = args.tag or (TAG_TXT.read_text().strip() if TAG_TXT.exists() else "unknown")
    out = Path(args.out) if args.out else INDEX_TSV
    with out.open("w", encoding="utf-8", newline="\n") as f:
        f.write(f"# laravel/framework {tag} src/Illuminate + config. "
                f"Generated by scripts/laravel_source.py index; do not edit.\n")
        for r in rows:
            f.write("\t".join(r).rstrip("\t") + "\n")
    if not args.out:
        TAG_TXT.write_text(tag + "\n")
    print(f"indexed {len(files)} files: {len(rows)} rows -> {out} ({tag})", file=sys.stderr)
    return 0


# ----------------------------------------------------------------------------
# check
# ----------------------------------------------------------------------------

class Index:
    def __init__(self, path: Path = INDEX_TSV):
        self.classes: dict[str, dict] = {}
        self.methods: dict[str, set[str]] = defaultdict(set)   # lowercased
        self.consts: dict[str, set[str]] = defaultdict(set)
        self.props: dict[str, set[str]] = defaultdict(set)
        self.functions: set[str] = set()
        self.facades: set[str] = set()
        self.aliases: dict[str, str] = {}
        self.commands: set[str] = set()
        self.config: dict[str, set[str]] = defaultdict(set)
        lines = path.read_text(encoding="utf-8").splitlines()
        m = re.match(r"# laravel/framework (\S+) ", lines[0] if lines else "")
        self.tag = m.group(1) if m else "?"
        for line in lines:
            if line.startswith("#") or not line:
                continue
            kind, a, b, c, d, e, f = (line.split("\t") + [""] * 6)[:7]
            if kind == "class":
                self.classes[a] = {
                    "kind": b,
                    "extends": [x for x in c.split(",") if x],
                    "implements": [x for x in d.split(",") if x],
                    "traits": [x for x in e.split(",") if x],
                    "mixins": [x for x in f.split(",") if x],
                }
            elif kind == "method":
                self.methods[a].add(b.lower())
            elif kind == "const":
                self.consts[a].add(b)
            elif kind == "prop":
                self.props[a].add(b)
            elif kind == "function":
                self.functions.add(a)
            elif kind == "facade":
                self.facades.add(a)
            elif kind == "alias":
                self.aliases[a] = b
            elif kind == "command":
                self.commands.add(a)
            elif kind == "config":
                self.config[a].add(b)
        self.by_short: dict[str, list[str]] = defaultdict(list)
        for fq in self.classes:
            self.by_short[fq.rsplit("\\", 1)[-1]].append(fq)
        self.namespaces = {fq.rsplit("\\", 1)[0] for fq in list(self.classes) + list(self.functions)}
        self.namespaces |= {ns.rsplit("\\", k)[0] for ns in list(self.namespaces) for k in range(1, ns.count("\\") + 1)}

    def known(self, fq: str) -> bool:
        return fq in self.classes or fq in self.functions

    def chain(self, fq: str) -> tuple[list[str], bool]:
        """Classes to search (parents, traits, mixins) and whether the chain stays in Illuminate."""
        seen: list[str] = []
        todo, closed = [fq], True
        while todo:
            c = todo.pop()
            if c in seen:
                continue
            info = self.classes.get(c)
            if info is None:
                closed = False
                continue
            seen.append(c)
            todo += info["extends"] + info["traits"] + info["mixins"]
            # An interface outside the index adds no callable member the class lacks.
            todo += [i for i in info["implements"] if i in self.classes]
        return seen, closed

    def has_member(self, fq: str, member: str, call: bool) -> bool | None:
        """True, False (provably missing) or None (cannot tell)."""
        if member.lower() in UNIVERSAL_MEMBERS:
            return True
        classes, closed = self.chain(fq)
        facade = fq in self.facades
        dynamic = False
        for c in classes:
            if member.startswith("$"):
                if member[1:] in self.props[c]:
                    return True
            elif call:
                if member.lower() in self.methods[c]:
                    return True
            elif member in self.consts[c] or member.lower() in self.methods[c]:
                return True
            if c in (MACROABLE,) or (facade and c == FACADE_BASE):
                continue
            if self.methods[c] & MAGIC:
                dynamic = True
        if not closed or dynamic:
            return None
        return False


def load_allow(path: Path = ALLOW_TSV) -> tuple[set[str], set[str]]:
    syms, lines = set(), set()
    if not path.exists():
        return syms, lines
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
            raise UsageError(f"{path.relative_to(REPO)}:{n}: allowlist rows need symbol<TAB>reason")
        key = parts[0].strip()
        (lines if re.search(r"\.md:\d+$", key) else syms).add(key)
    return syms, lines


FENCE = re.compile(r"^\s*(`{3,}|~{3,})\s*([\w+-]*)")
SPAN = re.compile(r"`([^`\n]+)`")
FQ = re.compile(rf"(?<![\w\\$])\\?(Illuminate(?:\\{IDENT})+)(\\\{{[^}}]*\}})?(?:::(\$?{IDENT})(\s*\()?)?")
SHORT = re.compile(rf"(?<![\w\\$>:])([A-Z]{IDENT})::(\$?{IDENT})(\s*\()?")
USE = re.compile(rf"^\s*use\s+(?:function\s+|const\s+)?(\\?{IDENT}(?:\\{IDENT})*)(?:\s+as\s+({IDENT}))?\s*;")
COMMAND = re.compile(r"(?<![\w-])artisan\s+([a-z_][a-z0-9_-]*(?::[a-z0-9_-]+)*)(?![\w:.-])")
ARTISAN_CALL = re.compile(r"Artisan::(?:call|queue)\(\s*['\"]([a-z_][a-z0-9_-]*(?::[a-z0-9_-]+)*)")
CONFIG = re.compile(r"(?:(?<![\w>$:])config|Config::(?:get|has|string|integer|float|boolean|array))\(\s*'([a-z_][\w-]*)\.([\w-]+)")
CODE_LANGS = {"php", "bash", "sh", "shell", "console", "zsh", "", "text", "blade", "yaml", "yml", "ini", "env"}


def scan_file(display: str, text: str, idx: Index, allow_syms: set[str], allow_lines: set[str],
              rel: str | None = None) -> list[str]:
    """Findings for one file; `rel` (repo-relative path) is what path.md:LINE allow keys match."""
    findings: list[str] = []

    def report(line_no: int, sym: str):
        if sym in allow_syms or f"{rel or display}:{line_no}" in allow_lines:
            return
        findings.append(f"{display}:{line_no}: {sym} not found in laravel/framework {idx.tag}")

    def check_fq(line_no: int, fq: str, group: str | None, member: str | None, call: bool):
        if group:
            for name in split_names(group.strip("\\{}")):
                full = f"{fq}\\{name.split(' as ')[0].strip()}"
                if not idx.known(full) and full not in idx.namespaces:
                    report(line_no, full)
            return
        if not idx.known(fq):
            if fq in idx.namespaces:
                return
            report(line_no, fq)
            return
        if member and fq in idx.classes and idx.has_member(fq, member, call) is False:
            report(line_no, f"{fq}::{member}" + ("()" if call else ""))

    def check_short(line_no: int, s: str, imports: dict[str, str]):
        for m in SHORT.finditer(s):
            short, member, call = m.group(1), m.group(2), bool(m.group(3))
            if short in imports:
                target = imports[short]
                if not target.startswith("Illuminate\\") or not idx.known(target):
                    continue  # app or package class; a missing Illuminate import is reported by FQ
                cands = [target]
            elif short in idx.aliases:
                cands = [idx.aliases[short]]
            else:
                cands = idx.by_short.get(short, [])
            cands = [c for c in cands if c in idx.classes]
            if not cands:
                continue
            if all(idx.has_member(c, member, call) is False for c in cands):
                label = cands[0] if len(cands) == 1 else short
                report(line_no, f"{label}::{member}" + ("()" if call else ""))

    def check_commands(line_no: int, s: str, php: bool):
        found = [m.group(1) for m in ARTISAN_CALL.finditer(s)]
        if not php:
            found += [m.group(1) for m in COMMAND.finditer(s)]
        for cmd in found:
            if cmd not in idx.commands:
                report(line_no, f"artisan {cmd}")

    def check_config(line_no: int, s: str):
        for m in CONFIG.finditer(s):
            file, key = m.group(1), m.group(2)
            if file in idx.config and file not in APP_OWNED_CONFIG and key not in idx.config[file]:
                report(line_no, f"config {file}.{key}")

    lines = text.splitlines()
    fence: str | None = None
    lang = ""
    imports: dict[str, str] = {}
    for n, line in enumerate(lines, 1):
        fm = FENCE.match(line)
        if fence is None and fm:
            fence, lang, imports = fm.group(1), fm.group(2).lower(), {}
            continue
        # A closing fence uses the opener's character, at least as many of them, and nothing else.
        closer = line.strip()
        if fence is not None and len(closer) >= len(fence) and closer == fence[0] * len(closer):
            fence = None
            continue
        # Fully qualified names are unambiguous: checked everywhere.
        for m in FQ.finditer(line):
            check_fq(n, m.group(1), m.group(2), m.group(3), bool(m.group(4)))
        if fence is not None:
            if lang not in CODE_LANGS:
                continue
            um = USE.match(line)
            if um:
                full = um.group(1).lstrip("\\")
                imports[um.group(2) or full.rsplit("\\", 1)[-1]] = full
            pieces = [line]
            php = lang in {"php", "blade"}
        else:
            pieces = SPAN.findall(line)
            php = False
        for s in pieces:
            check_short(n, s, imports if fence is not None else {})
            check_commands(n, s, php)
            check_config(n, s)
    return findings


def cmd_check(args) -> int:
    if not INDEX_TSV.exists():
        raise UsageError("no index: run sh scripts/refresh-laravel-data.sh")
    idx = Index()
    tag = TAG_TXT.read_text().strip() if TAG_TXT.exists() else "?"
    if tag != idx.tag:
        raise UsageError(f"index is for laravel/framework {idx.tag}, tag file says {tag}: rerun the refresh")
    allow_syms, allow_lines = load_allow()
    targets: list[tuple[str, Path]] = []
    for given in (args.paths or DEFAULT_TARGETS):
        p = Path(given) if Path(given).is_absolute() else REPO / given
        if p.is_file():
            targets.append((given, p))
        elif p.is_dir():
            for f in sorted(p.rglob("*.md")):
                targets.append((str(Path(given) / f.relative_to(p)), f))
        elif args.paths:
            raise UsageError(f"{given}: no such file or directory")
    findings: list[str] = []
    for display, path in targets:
        try:
            rel = path.resolve().relative_to(REPO).as_posix()
        except ValueError:
            rel = display
        findings += scan_file(display, path.read_text(encoding="utf-8"), idx, allow_syms, allow_lines, rel)
    for f in findings:
        print(f)
    print(f"{len(findings)} unknown symbol(s) in {len(targets)} file(s) (laravel/framework {idx.tag})")
    return 1 if findings else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    i = sub.add_parser("index", help="build the index from a laravel/framework checkout")
    i.add_argument("src")
    i.add_argument("--tag", help="the laravel/framework tag the source is from")
    i.add_argument("--out", help="write here instead of scripts/data/ (the tag file is left alone)")
    c = sub.add_parser("check", help="check markdown files or directories against the index")
    c.add_argument("paths", nargs="*")
    try:
        args = ap.parse_args()
    except SystemExit as e:
        return 2 if e.code else 0
    if not args.cmd:
        ap.print_usage(sys.stderr)
        return 2
    try:
        return {"index": cmd_index, "check": cmd_check}[args.cmd](args)
    except UsageError as e:
        print(f"laravel_source.py: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
