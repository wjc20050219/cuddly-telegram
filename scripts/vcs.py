#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Minimal git commit driver built on dulwich (pure Python).

本机没有 git 可执行文件，WSL 也不可用，但没有版本控制就无法回滚任何改动。
dulwich 是纯 Python 的 git 实现，安装到 `.tools/pylibs`（不入库），
本脚本用它完成 init / status / add / commit，并**遵守 .gitignore**。

用法：
    python scripts/vcs.py status
    python scripts/vcs.py add <path>...
    python scripts/vcs.py commit "<message>"
    python scripts/vcs.py log [-n N]
    python scripts/vcs.py remote [add <name> <url>]
    python scripts/vcs.py push [<remote>] [<local>:<remote_branch>]

关于 push：本机同样没有 git，推送同样由 dulwich 完成。走 SSH 时
dulwich 会调用系统 `ssh`，因此把选项（私钥、known_hosts）通过
`GIT_SSH_COMMAND` 传给子进程；该变量由 dulwich 自己在建立 SSH 连接时读取。
"""

from __future__ import print_function

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, ".tools", "pylibs"))

try:
    from dulwich.repo import Repo
    from dulwich import porcelain
except ImportError as exc:  # pragma: no cover - environment guard
    sys.stderr.write(
        "需要 dulwich：python -m pip install --target .tools/pylibs dulwich\n"
        "（离线可用：先 pip download，再 --no-index --find-links）\n"
        "原始错误：%s\n" % (exc,)
    )
    raise SystemExit(2)


def _repo():
    if not os.path.isdir(os.path.join(ROOT, ".git")):
        return Repo.init(ROOT, mkdir=False)
    return Repo(ROOT)


def _status_paths(st):
    """把 dulwich 的 GitStatus 归一化成 (untracked, changed) 两个路径列表。

    dulwich 的字段类型在不同版本间不一致：`untracked` 是 list，
    而 `unstaged`/`staged` 既可能是 list 也可能是 dict。
    我最初按 dict 迭代 `unstaged`，结果拿到的是**整数下标**，
    直到 porcelain.add 抛 `TypeError: expected str ... not int` 才暴露。
    这里显式兼容两种形态。
    """
    def _as_paths(value):
        if value is None:
            return []
        if isinstance(value, dict):
            out = []
            for group in value.values():
                out.extend(group or [])
            return out
        return list(value)

    untracked = [p.decode("utf-8", "replace") if isinstance(p, bytes) else p
                 for p in _as_paths(getattr(st, "untracked", None))]
    changed = []
    for attr in ("unstaged", "staged"):
        for p in _as_paths(getattr(st, attr, None)):
            if not isinstance(p, (str, bytes)):
                continue
            changed.append(p.decode("utf-8", "replace") if isinstance(p, bytes) else p)
    return untracked, changed


def cmd_status(argv):
    r = _repo()
    st = porcelain.status(r)
    try:
        branch = porcelain.active_branch(r).decode("utf-8", "replace")
    except Exception:
        branch = "(未知)"
    untracked, changed = _status_paths(st)
    print("branch : %s" % branch)
    print("untracked (%d):" % len(untracked))
    for p in untracked[:40]:
        print("   %s" % p)
    if len(untracked) > 40:
        print("   ... and %d more" % (len(untracked) - 40))
    uniq = sorted(set(changed))
    print("changed   (%d)" % len(uniq))
    for p in uniq[:40]:
        print("   %s" % p)
    return 0


def cmd_add(argv):
    if not argv:
        sys.stderr.write("add 需要至少一个路径\n")
        return 2
    r = _repo()
    paths = []
    for a in argv:
        full = os.path.join(ROOT, a)
        if os.path.isdir(full):
            paths.append(a.replace("\\", "/"))
        else:
            paths.append(a.replace("\\", "/"))
    porcelain.add(r, paths=paths)
    print("added: %s" % ", ".join(paths))
    return 0


def cmd_commit(argv):
    if not argv:
        sys.stderr.write("commit 需要一条提交信息\n")
        return 2
    msg = argv[0]
    r = _repo()
    # 必须同时 add **未跟踪**与**已跟踪但被修改**的文件。
    # 这里踩过一个很隐蔽的坑：dulwich 的 porcelain.commit **不会**自动
    # 把已跟踪文件的改动写入索引，只 add 未跟踪项会提交出一个
    # "只新增文件、不含任何修改"的提交——提交成功、有 SHA、但改动全丢。
    # 我是在校验提交内容（对比父子树）时才发现第二个提交的 changed 为空。
    st = porcelain.status(r)
    untracked, changed = _status_paths(st)
    add_paths = []
    for p in list(untracked) + list(changed):
        if p and os.path.exists(os.path.join(ROOT, p)):
            add_paths.append(p)
    add_paths = sorted(set(add_paths))
    if add_paths:
        porcelain.add(r, paths=add_paths)
    staged = porcelain.status(r).staged
    cid = porcelain.commit(
        r,
        message=msg.encode("utf-8"),
        author=b"RiceVar-ID <ricevar@localhost>",
        committer=b"RiceVar-ID <ricevar@localhost>",
    )
    print("committed %s" % cid.decode("ascii"))
    print("staged paths: %d" % len(add_paths))
    return 0


def cmd_log(argv):
    n = 10
    if len(argv) >= 2 and argv[0] == "-n":
        n = int(argv[1])
    r = _repo()
    try:
        head = r.head()
    except KeyError:
        print("(还没有任何提交)")
        return 0
    walker = r.get_walker()
    for i, entry in enumerate(walker):
        if i >= n:
            break
        c = entry.commit
        first = c.message.decode("utf-8", "replace").splitlines()[0]
        print("%s  %s" % (c.id.decode("ascii")[:12], first))
    return 0


def cmd_remote(argv):
    """查看或设置远程仓库地址。

    dulwich 的 ConfigFile 不会替我们建 [remote "origin"] 段，
    所以"关联远程仓库"这一步必须显式写入配置。
    """
    r = _repo()
    cfg = r.get_config()
    if not argv:
        found = False
        try:
            sections = cfg.sections()
        except Exception:
            sections = []
        for name in (b"origin", b"upstream"):
            if (b"remote", name) in sections:
                url = cfg.get((b"remote", name), b"url")
                print("%s\t%s" % (name.decode("ascii"),
                                  url.decode("utf-8", "replace")))
                found = True
        if not found:
            print("(没有配置任何远程仓库)")
        return 0

    if len(argv) >= 3 and argv[0] == "add":
        name, url = argv[1], argv[2]
        cfg.set((b"remote", name.encode("ascii")), b"url",
                url.encode("utf-8"))
        cfg.set((b"remote", name.encode("ascii")), b"fetch",
                b"+refs/heads/*:refs/remotes/%s/*" % name.encode("ascii"))
        cfg.write_to_path()
        print("remote %s -> %s" % (name, url))
        return 0

    sys.stderr.write("用法：remote | remote add <name> <url>\n")
    return 2


def cmd_push(argv):
    """把本地分支推送到远程（dulwich 实现，本机无 git 可执行文件）。"""
    r = _repo()
    remote = argv[0] if len(argv) >= 1 else "origin"
    cfg = r.get_config()
    try:
        url = cfg.get((b"remote", remote.encode("ascii")), b"url")
    except KeyError:
        sys.stderr.write(
            "未配置远程 %s。先执行：\n"
            "  python scripts/vcs.py remote add %s <url>\n" % (remote, remote))
        return 2

    local = porcelain.active_branch(r).decode("utf-8", "replace")
    if len(argv) >= 2 and ":" in argv[1]:
        local, remote_branch = argv[1].split(":", 1)
    elif len(argv) >= 2:
        remote_branch = argv[1]
    else:
        remote_branch = local

    refspec = ("refs/heads/%s:refs/heads/%s" % (local, remote_branch)).encode("ascii")
    print("push %s -> %s (%s)" % (local, remote, url.decode("utf-8", "replace")))
    result = porcelain.push(r, url.decode("utf-8"), refspecs=[refspec])
    for ref, status in sorted(result.items()):
        print("  %s  %s" % (ref.decode("utf-8", "replace"), status))
    return 0


COMMANDS = {
    "status": cmd_status,
    "add": cmd_add,
    "commit": cmd_commit,
    "log": cmd_log,
    "remote": cmd_remote,
    "push": cmd_push,
}


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(argv) >= 2 else 2
    fn = COMMANDS.get(argv[1])
    if fn is None:
        sys.stderr.write("未知子命令：%s\n可选：%s\n" % (argv[1], ", ".join(sorted(COMMANDS))))
        return 2
    return fn(argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
