#!/usr/bin/env python3
"""build_matrices.py —— 把服务器上的逐样本深度 BED 汇总成特征矩阵。

用法:
  build_matrices.py depth   --depth-dir DIR --out OUT.parquet [--pattern 'w10000.regions.bed.gz']
  build_matrices.py check   --parquet FILE

SNP 矩阵由 scripts/select_snp_markers.py 从联合多样本 VCF 生成；本模块不接受
variant-only 单样本 VCF，以免把“未出现”错误解释为缺失或 0/0。

设计原则:
  - 行 = 窗口 / 标记，列 = 样本（与本机分析代码的约定一致）
  - 深度矩阵用 int16（深度×10，保留一位小数），显著压缩体积
"""
import argparse
import glob
import gzip
import os
import sys

import numpy as np
import pandas as pd


def read_regions_bed(path):
    """读 mosdepth .regions.bed.gz -> (keys, depths)；keys = (chrom, start, end)"""
    op = gzip.open if path.endswith(".gz") else open
    chrom, start, end, dep = [], [], [], []
    with op(path, "rt") as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 4:
                continue
            chrom.append(f[0])
            start.append(int(f[1]))
            end.append(int(f[2]))
            dep.append(float(f[3]))
    key = pd.MultiIndex.from_arrays([chrom, start, end], names=["chrom", "start", "end"])
    return key, np.asarray(dep, dtype=np.float32)


def build_depth_matrix(depth_dir, out, pattern):
    # 支持两种布局：DIR/<sample>/<pattern> 与 DIR/<sample>.regions.bed.gz。
    files = sorted(glob.glob(os.path.join(depth_dir, "*", pattern)))
    direct_layout = False
    if not files:
        files = sorted(glob.glob(os.path.join(depth_dir, pattern)))
        direct_layout = True
    if not files:
        sys.exit(f"没有匹配到文件: {depth_dir}/*/{pattern} 或 {depth_dir}/{pattern}")
    print(f"发现 {len(files)} 个样本文件", flush=True)

    ref_key = None
    cols, names = [], []
    for i, fp in enumerate(files, 1):
        if direct_layout:
            sid = os.path.basename(fp).split(".regions.bed")[0]
        else:
            sid = os.path.basename(os.path.dirname(fp))
        key, dep = read_regions_bed(fp)
        if ref_key is None:
            ref_key = key
        elif not key.equals(ref_key):
            print(f"  ! {sid} 的窗口坐标/顺序与首个样本不一致，跳过", flush=True)
            continue
        cols.append(dep)
        names.append(sid)
        if i % 20 == 0:
            print(f"  已读 {i}/{len(files)}", flush=True)

    mat = np.vstack(cols).T if cols else np.zeros((0, 0), dtype=np.float32)
    # 深度 ×10 存成 int16（0–3276.7×），体积减半
    mat_i = np.clip(np.rint(mat * 10.0), 0, 32767).astype(np.int16)
    df = pd.DataFrame(mat_i, index=ref_key, columns=names)
    df.index.name = "chrom"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if out.endswith(".parquet"):
        df.reset_index().to_parquet(out, index=False, compression="zstd")
    else:
        df.to_csv(out, sep="\t")
    size = os.path.getsize(out)
    print(f"写出 {out}: {df.shape[0]} 窗口 × {df.shape[1]} 样本, {size/1048576:.1f} MB (深度=值/10)")
    return df



def check(parquet):
    df = pd.read_parquet(parquet)
    print(f"shape={df.shape}")
    print(df.iloc[:3, :5])
    print("列（样本）:", list(df.columns)[:10])
    num = df.select_dtypes("number")
    if not num.empty:
        print(f"深度统计（/10）: min={num.min().min()/10:.2f} max={num.max().max()/10:.2f} "
              f"mean={num.mean().mean()/10:.2f}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("depth")
    p1.add_argument("--depth-dir", required=True)
    p1.add_argument("--out", required=True)
    p1.add_argument("--pattern", required=True)

    p3 = sub.add_parser("check")
    p3.add_argument("--parquet", required=True)

    a = ap.parse_args()
    if a.cmd == "depth":
        build_depth_matrix(a.depth_dir, a.out, a.pattern)
    elif a.cmd == "check":
        check(a.parquet)


if __name__ == "__main__":
    main()
