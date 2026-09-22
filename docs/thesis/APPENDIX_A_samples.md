# 附录 A　样本清单与 run 号

> 本附录由 `scripts/build_appendix_samples.py` 从
> `data/metadata/server/pilot_manifest.tsv` 与
> `data/metadata/server/independent_manifest.tsv` 自动生成，**请勿手工编辑**。
> 生成时会重新校验面板规模、品种零重叠、全部双端与最低深度等不变量，
> 任一不变量不满足则不生成文件，以避免正文与附录静默不一致。

生成脚本：`python scripts/build_appendix_samples.py`

## A.1 面板构成与不变量

| 项目 | Pilot | 独立面板 | 合计 |
| --- | --- | --- | --- |
| 样本数 | 30 | 25 | 55 |
| 品种数 | 30 | 25 | 55 |
| 品种交集 | — | — | **0** |
| 测序布局 | 全部 PAIRED | 全部 PAIRED | 全部 PAIRED |
| 最低估计深度 | 20.00× | 20.02× | — |
| 清单声明大小 | 170.70 GiB | 164.02 GiB | **334.71 GiB** |

> **声明大小**为 ENA/SRA 清单中 `fastq_bytes` 字段之和（双端按 `;` 拆分后相加），
> 用于评估服务器存储需求，**不是实测下载量**。实际字节数须以服务器上
> `download_log.tsv` 的记录为准。

### A.2 Pilot 面板样本（30 份，用于位点冻结与闭集深度曲线）

| # | sample_id | run_accession | variety_name | subspecies | platform | 布局 | 估计深度 | 读长 | 声明大小 (GiB) | 来源库 | BioProject |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `SRR34854884` | `SRR34854884` | Nangeng46 | temperate_japonica | BGISEQ | PAIRED | 38.49× | 300.0 | 10.27 | NCBI_SRA | PRJNA1301070 |
| 2 | `SRR34854885` | `SRR34854885` | Hugeng137 | temperate_japonica | BGISEQ | PAIRED | 38.24× | 300.0 | 12.33 | NCBI_SRA | PRJNA1301070 |
| 3 | `SRR13189454` | `SRR13189454` | Kola Joha | aromatic | ILLUMINA | PAIRED | 35.36× | 302.0 | 6.77 | NCBI_SRA | PRJNA678305 |
| 4 | `SRR22201068` | `SRR22201068` | Koshihijar | japonica | ILLUMINA | PAIRED | 31.07× | 300.0 | 6.16 | NCBI_SRA | PRJNA894819 |
| 5 | `SRR22201066` | `SRR22201066` | Yanggeng4227 | japonica | ILLUMINA | PAIRED | 30.75× | 300.0 | 6.12 | NCBI_SRA | PRJNA894819 |
| 6 | `SRR6983858` | `SRR6983858` | Xiushui 110 | japonica | ILLUMINA | PAIRED | 29.24× | 200.0 | 9.03 | NCBI_SRA | PRJNA448500 |
| 7 | `SRR19502944` | `SRR19502944` | V559_Nanfangchangligeng | japonica | ILLUMINA | PAIRED | 28.77× | 300.0 | 8.11 | NCBI_SRA | PRJNA844290 |
| 8 | `SRR2544584` | `SRR2544584` | RP Bio-226 | indica | ILLUMINA | PAIRED | 27.94× | 302.0 | 6.45 | NCBI_SRA | PRJNA285384 |
| 9 | `SRR18272552` | `SRR18272552` | Sherpa | aus | ILLUMINA | PAIRED | 27.85× | 302.0 | 4.86 | NCBI_SRA | PRJNA813905 |
| 10 | `DRR092499` | `DRR092499` | Bekogonomi | indica | ILLUMINA | PAIRED | 27.57× | 300.0 | 5.24 | DDBJ | PRJDB5765 |
| 11 | `SRR567751` | `SRR567751` | Minghui | indica | ILLUMINA | PAIRED | 26.47× | 180.0 | 8.57 | NCBI_SRA | PRJNA174121 |
| 12 | `SRR22201097` | `SRR22201097` | Jinkeyou651 | indica | ILLUMINA | PAIRED | 24.76× | 300.0 | 5.06 | NCBI_SRA | PRJNA894819 |
| 13 | `SRR19503114` | `SRR19503114` | V074_Kuiku131 | japonica | ILLUMINA | PAIRED | 22.99× | 200.0 | 7.07 | NCBI_SRA | PRJNA844290 |
| 14 | `SRR15040831` | `SRR15040831` | 19W35 | indica | ILLUMINA | PAIRED | 22.65× | 299.7 | 2.84 | NCBI_SRA | PRJNA743713 |
| 15 | `DRR179816` | `DRR179816` | BOUZU 1 | japonica | ILLUMINA | PAIRED | 22.21× | 300.0 | 4.69 | DDBJ | PRJDB8365 |
| 16 | `SRR15040811` | `SRR15040811` | 19W70 | indica | ILLUMINA | PAIRED | 21.74× | 299.7 | 2.77 | NCBI_SRA | PRJNA743713 |
| 17 | `SRR17344245` | `SRR17344245` | Santhi 990 | aus | ILLUMINA | PAIRED | 21.61× | 180.0 | 7.01 | NCBI_SRA | PRJNA792623 |
| 18 | `SRR17344239` | `SRR17344239` | Spin Mere | aus | ILLUMINA | PAIRED | 21.55× | 180.0 | 7.01 | NCBI_SRA | PRJNA792623 |
| 19 | `SRR32126008` | `SRR32126008` | P 32::GSOR 311085-G1 | admixed | ILLUMINA | PAIRED | 21.54× | 202.0 | 6.84 | NCBI_SRA | PRJNA1214498 |
| 20 | `SRR17344256` | `SRR17344256` | C.B. II | aus | ILLUMINA | PAIRED | 21.52× | 180.0 | 7.13 | NCBI_SRA | PRJNA792623 |
| 21 | `SRR33723419` | `SRR33723419` | Yamuna | indica | ILLUMINA | PAIRED | 21.28× | 302.0 | 3.15 | NCBI_SRA | PRJNA1268320 |
| 22 | `SRR19502941` | `SRR19502941` | V057_Kendao12 | japonica | ILLUMINA | PAIRED | 21.16× | 200.0 | 6.51 | NCBI_SRA | PRJNA844290 |
| 23 | `SRR15040869` | `SRR15040869` | Jiangxiang1 | indica | ILLUMINA | PAIRED | 20.82× | 299.7 | 2.65 | NCBI_SRA | PRJNA743713 |
| 24 | `SRR25567266` | `SRR25567266` | Gaekjujodo | unknown | ILLUMINA | PAIRED | 20.03× | 302.0 | 2.61 | NCBI_SRA | PRJNA1003283 |
| 25 | `SRR12523534` | `SRR12523534` | Gangxiang1A | unknown | ILLUMINA | PAIRED | 20.03× | 300.0 | 3.22 | NCBI_SRA | PRJNA656900 |
| 26 | `DRR771401` | `DRR771401` | Long Japonica 13 | japonica | ILLUMINA | PAIRED | 20.02× | 299.6 | 2.80 | DDBJ | PRJDB36518 |
| 27 | `SRR22440195` | `SRR22440195` | Ganggye 12 | unknown | ILLUMINA | PAIRED | 20.02× | 300.0 | 5.94 | NCBI_SRA | PRJNA896894 |
| 28 | `SRR12523904` | `SRR12523904` | LT4 | unknown | ILLUMINA | PAIRED | 20.02× | 300.0 | 3.31 | NCBI_SRA | PRJNA656900 |
| 29 | `SRR22223604` | `SRR22223604` | G41761 | unknown | ILLUMINA | PAIRED | 20.00× | 300.0 | 3.10 | NCBI_SRA | PRJNA896343 |
| 30 | `SRR12524065` | `SRR12524065` | Xiangzaoxian13hao | unknown | ILLUMINA | PAIRED | 20.00× | 300.0 | 3.10 | NCBI_SRA | PRJNA656900 |

### A.3 独立面板样本（25 份，用于开放集拒识）

| # | sample_id | run_accession | variety_name | subspecies | platform | 布局 | 估计深度 | 读长 | 声明大小 (GiB) | 来源库 | BioProject |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `SRR27987055` | `SRR27987055` | jg818 | japonica | ILLUMINA | PAIRED | 42.82× | 295.4 | 10.79 | NCBI_SRA | PRJNA1077238 |
| 2 | `SRR5486789` | `SRR5486789` | Tam Xoan Hai Hau | japonica | ILLUMINA | PAIRED | 41.22× | 200.0 | 12.37 | NCBI_SRA | PRJNA384811 |
| 3 | `SRR5463094` | `SRR5463094` | Longdao24 | japonica | ILLUMINA | PAIRED | 40.91× | 299.9 | 8.11 | NCBI_SRA | PRJNA383779 |
| 4 | `SRR28514681` | `SRR28514681` | LB | indica | ILLUMINA | PAIRED | 37.97× | 296.5 | 5.12 | NCBI_SRA | PRJNA1094905 |
| 5 | `DRR092498` | `DRR092498` | Akidawara | indica | ILLUMINA | PAIRED | 37.17× | 200.0 | 11.12 | DDBJ | PRJDB5765 |
| 6 | `SRR2029574` | `SRR2029574` | Huanghuazhan:HM2-S125 | indica | ILLUMINA | PAIRED | 37.13× | 200.0 | 10.49 | NCBI_SRA | PRJNA283022 |
| 7 | `SRR2543336` | `SRR2543336` | Ble te lo | japonica | ILLUMINA | PAIRED | 35.63× | 200.0 | 10.26 | NCBI_SRA | PRJNA296753 |
| 8 | `SRR5486790` | `SRR5486790` | Tam Xoan Bac Ninh | japonica | ILLUMINA | PAIRED | 35.61× | 200.0 | 10.85 | NCBI_SRA | PRJNA384811 |
| 9 | `SRR2529343` | `SRR2529343` | Chiem Nho Bac Ninh 2 | indica | ILLUMINA | PAIRED | 34.47× | 200.0 | 10.26 | NCBI_SRA | PRJNA296753 |
| 10 | `SRR24504128` | `SRR24504128` | Jia58 | japonica | ILLUMINA | PAIRED | 33.16× | 300.0 | 3.82 | NCBI_SRA | PRJNA956682 |
| 11 | `SRR2543299` | `SRR2543299` | Nep Lun | indica | ILLUMINA | PAIRED | 30.10× | 200.0 | 8.91 | NCBI_SRA | PRJNA296753 |
| 12 | `ERR10368528` | `ERR10368528` | Vandana | indica | ILLUMINA | PAIRED | 28.60× | 98.9 | 7.45 | ENA | PRJEB56693 |
| 13 | `SRR30280100` | `SRR30280100` | Induced haploid 5 | unknown | DNBSEQ | PAIRED | 20.17× | 300.0 | 5.23 | NCBI_SRA | PRJNA1147860 |
| 14 | `DRR771469` | `DRR771469` | NG718 | unknown | ILLUMINA | PAIRED | 20.15× | 299.0 | 3.04 | DDBJ | PRJDB36518 |
| 15 | `SRR32361556` | `SRR32361556` | DN9_118 | unknown | ILLUMINA | PAIRED | 20.13× | 300.0 | 3.32 | NCBI_SRA | PRJNA1224316 |
| 16 | `SRR22440327` | `SRR22440327` | Ganggye 3 | unknown | ILLUMINA | PAIRED | 20.13× | 300.0 | 5.96 | NCBI_SRA | PRJNA896894 |
| 17 | `SRR9943889` | `SRR9943889` | Tak Siah | unknown | ILLUMINA | PAIRED | 20.13× | 202.0 | 6.02 | NCBI_SRA | PRJNA422249 |
| 18 | `SRR22440367` | `SRR22440367` | Heocheon4 | unknown | ILLUMINA | PAIRED | 20.10× | 300.0 | 5.94 | NCBI_SRA | PRJNA896894 |
| 19 | `SRR25567107` | `SRR25567107` | Yejo | unknown | ILLUMINA | PAIRED | 20.09× | 302.0 | 2.68 | NCBI_SRA | PRJNA1003283 |
| 20 | `SRR6220456` | `SRR6220456` | cultivated_rice_128 | unknown | ILLUMINA | PAIRED | 20.09× | 250.0 | 5.64 | NCBI_SRA | PRJNA407820 |
| 21 | `SRR11131409` | `SRR11131409` | US_L202 | unknown | ILLUMINA | PAIRED | 20.05× | 199.1 | 4.28 | NCBI_SRA | PRJNA603026 |
| 22 | `DRR771445` | `DRR771445` | DN2323 | unknown | ILLUMINA | PAIRED | 20.04× | 299.2 | 2.86 | DDBJ | PRJDB36518 |
| 23 | `SRR24060283` | `SRR24060283` | ART71-96-1-1-B-B | unknown | ILLUMINA | PAIRED | 20.04× | 289.3 | 3.71 | NCBI_SRA | PRJNA951930 |
| 24 | `SRR25567193` | `SRR25567193` | Sura | unknown | ILLUMINA | PAIRED | 20.03× | 302.0 | 2.64 | NCBI_SRA | PRJNA1003283 |
| 25 | `SRR22223553` | `SRR22223553` | G41971 | unknown | ILLUMINA | PAIRED | 20.02× | 300.0 | 3.14 | NCBI_SRA | PRJNA896343 |

## A.4 预检样本集

为降低「先跑通流程再上量」的风险，另设两个预检样本集：

| 名称 | 样本数 | 声明大小 | 用途 |
| --- | --- | --- | --- |
| `pilot_smoke1.tsv` | 1 | 2.61 GiB | 单样本端到端跑通 |
| `pilot_smoke5.tsv` | 5 | 23.19 GiB | 跨亚种流程验证 |

构成与选取规则见 `data/metadata/server/manifest_build_summary.json`。

## A.5 说明

1. `sample_id` 为 ENA/SRA 样本号，`run_accession` 为实际下载的 run 号；
   本文一个样本对应一个 run，无多样本合并。
2. `subspecies` 取自公共数据库元数据标注，**未经基因型判定**；
   标注为 `unknown` 的样本不做推测。
3. `estimated_depth` 由清单声明的碱基总数与参考基因组大小 374,495,335 bp
   （IRGSP-1.0）估算，属**清单声明值**，非实测比对深度；
   实测深度由 `mosdepth` 在 3.3 节给出。
4. 本清单中的品种名仅代表**元数据标签**，未经品种权或种子法意义确认；
   同名异种与同种异名的处理见 2.1.2 节与附录 D。
