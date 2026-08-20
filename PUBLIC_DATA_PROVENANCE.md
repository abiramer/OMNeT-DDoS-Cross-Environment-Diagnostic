# Public data provenance

This document contains aggregate provenance only. It includes no CICDDoS2019
source row, selected row, prepared row, split row, or prediction row.

## Acquisition

- Dataset: CIC-DDoS2019 / CICDDoS2019.
- Official page: <https://www.unb.ca/cic/datasets/ddos-2019.html>.
- Page verified/accessed for this release audit: 2026-08-19.
- Official CSV archive names used locally: `CSV-01-12.zip` and
  `CSV-03-11.zip`.
- Source organization: 18 CSV files under `day1/01-12` and `day2/03-11`.
- Users must obtain the dataset independently and comply with the terms and
  citation requirements stated by the Canadian Institute for Cybersecurity.

Raw CSV/ZIP files are excluded from this package. The source-file hashes below
permit a reader to verify an independently obtained copy.

## Official input inventory

| Source file | Bytes | Rows | Invalid required-8/label | Within-file exact duplicates | SHA-256 |
|---|---|---|---|---|---|
| day1/01-12/DrDoS_DNS.csv | 2133307948 | 5074413 | 162394 | 0 | eee1a2cf10be29129f00930e250236c237b97d2941e8cea766006db82047df83 |
| day1/01-12/DrDoS_LDAP.csv | 917302277 | 2181542 | 38650 | 0 | fbc836bfb01d9eb5f5a2b4aae3428d7c17f449ede5466273249a9ce6095338b0 |
| day1/01-12/DrDoS_MSSQL.csv | 1889181756 | 4524498 | 126466 | 0 | 534ebd8bb98a571b6e0a65a65091cb22b09156fa4db82e5752a92df02ea5402b |
| day1/01-12/DrDoS_NTP.csv | 645008606 | 1217007 | 7046 | 0 | b4ae33b2a22975f2c4c8b0e2bfc501fee38dae274dca37d4b01010de059c9c2c |
| day1/01-12/DrDoS_NetBIOS.csv | 1697479829 | 4094986 | 129853 | 0 | b0dbf6d712a021380cade45f753531a5860d0bfd4d338b4013ea5566d968329e |
| day1/01-12/DrDoS_SNMP.csv | 2172579815 | 5161377 | 10623 | 0 | a74a411a37fbb1a4d4acd20bb8a7e93714992e34d9fb08b3b2c5e1795c867eb7 |
| day1/01-12/DrDoS_SSDP.csv | 1252686219 | 2611374 | 42050 | 0 | 0bc1a2bb6dbef3851b7a2177ef74bd801dcf592b69ef5bbe5044821e695423c1 |
| day1/01-12/DrDoS_UDP.csv | 1506039371 | 3136802 | 40673 | 0 | 85c54bf54f987586e1d8da14b76d1167baa4636755cae24e648067e5242d679a |
| day1/01-12/Syn.csv | 637312127 | 1582681 | 202317 | 0 | 05a272a7005be14262d3929ad16877db42fc74a03032a3a5b58d0230ab08896a |
| day1/01-12/TFTP.csv | 9302011115 | 20107827 | 566761 | 0 | b56314cca3f68c9027e9fa684c7c565df6fc5c510c87f12b1c00390364e44d7c |
| day1/01-12/UDPLag.csv | 157968770 | 370605 | 36403 | 0 | f67708a8462509932759ffed7eb92dca0f423267609d1be38a461708d4ea5b7e |
| day2/03-11/LDAP.csv | 871398918 | 2113234 | 54112 | 0 | d1cfc7cb9252b73d9789f7307d7583be9c3a8e90ee9c096eefe8b0d3d8be23c3 |
| day2/03-11/MSSQL.csv | 2386225228 | 5775786 | 202217 | 0 | d13cf30e7b987f7e916c54643f2e03dd4c31fc4b2051be175d5ee83d392d8f88 |
| day2/03-11/NetBIOS.csv | 1418468105 | 3455899 | 130560 | 0 | ddd2e8cd76c125e1d93094af519845e2ed1eaf44edcd3f783b3a9dee638a5e1e |
| day2/03-11/Portmap.csv | 78611080 | 191694 | 9800 | 0 | d0148da21f3c645b32b21b59386721eddd497a16e3de4e2950391e575fca2e28 |
| day2/03-11/Syn.csv | 1877372065 | 4320541 | 283076 | 482799 | 603648e7c56e9232b6d647470dc01b6451502c594a4ebf235b45103edb5e545a |
| day2/03-11/UDP.csv | 1792797298 | 3782206 | 77047 | 0 | 27e262e851f12a5fc29cd433fec53a63e9e8fc3cfdc1a1d78f77995bd175a59b |
| day2/03-11/UDPLag.csv | 319793413 | 725165 | 50702 | 0 | c8a471f56721118dc0c5ae86ae348cd261f81cf7313c08f5bbdf913005ce7ced |

The 18 official CSVs contain **70,427,637 rows**.
An ancillary 93-byte LibreOffice-style lock metadata file was present locally,
was not a CICFlowMeter CSV, and was excluded from preparation and from this
public inventory. A raw inventory report initially marked the directory
invalid because of that ancillary file; independent validation then accepted
the 18 official CSVs and recorded status `valid`.

## Cleaning, deduplication, and balancing

| Stage | BENIGN | DDoS |
|---|---:|---:|
| raw | 113,828 | 70,313,809 |
| clean finite/valid | 112,731 | 68,144,156 |
| invalid removed | 1,097 | 2,169,653 |
| exact duplicates removed | 4,350 | 440,457 |
| clean unique | 108,381 | 67,703,699 |
| selected | 108,381 | 108,381 |

Headers and field strings were stripped of surrounding whitespace. Finite-value
validation required the complete eight-feature superset plus label. Exact
duplicates were determined by equality over all 88 normalized source fields,
not only the selected features; source metadata was excluded from identity.
The deterministic representative was the lowest day/source-file/original-row
tuple. Hash collisions were treated as fatal.

The final `N` is **108,381**: every clean unique BENIGN record was
retained, and exactly `N` DDoS records were selected without replacement. DDoS
allocation was proportional across day/source-file/attack strata using
Hamilton largest remainder, followed by a deterministic SHA-256 rank using
sampling seed `104729`. No BENIGN or DDoS row was
oversampled or duplicated.

Original `BENIGN` maps to binary `0`; every validated attack label maps to
binary `1` (`DDoS`). Source label/attack type is retained in private provenance.

## Frozen grouping and leakage prevention

Grouping fields were day, source file, source attack label, and the derived
`source_group` (source file/capture group). Each of the ten seeds searched only
source-group holdouts for a class-preserving split near 20%; there was no
record-level fallback. The same selected rows and partition per seed were used
for feature sets 4/6/8 and all model families.

Seeds: 104729, 130363, 155921, 181081, 206369, 231701, 257053, 282427, 307759, 333019.

Independent validation reported 31/31 checks and zero sample-ID, full-record
row-hash, and source-group overlap in every split. Aggregate group composition
and leakage evidence are under `evidence/provenance/`.

## Dataset-derived hashes

These hashes identify locally regenerated artifacts that are intentionally not
distributed here:

- prepared feature table: `56c90ab907c76567b7f26cf761ad45695c0b8e3ebe732ed43b04f5f8be74ca7b`;
- selected-row manifest: `902c22d120dff65c5529fd0e123622a6122531d5ce5589021e987ee1b52b3575`;
- split manifest: `0ecb7978ab509151cc1f2b4e2fbabe6b2ef98450597be8f4999d82ab92d383b5`;
- cleaning report: `98fb1f2a2eb0676da26628aa3d3160b87b9ad335b4c0a9e92f2f886d7a007cfa`;
- deduplication report: `637eb6673abfcab6f623ed729e25ea8d8a28476f5f73c0b1e5ac788d9323e953`;
- DDoS allocation report: `2bd116a03588f25c7998ab8a496e0201f68cdc395014f34e00905c4a13d7d2f8`;
- split composition report: `4e79fcc18af0fa016df5efc03fad5afeb7779dc51fcfd2071de03626795272de`;
- leakage report: `9e4218c20052793fb7ca733d0fbc1ce9f726059dbdcba4c03969d75a4189ab8d`.

## Excluded dataset-derived files and regeneration

Excluded: raw archives/CSVs, the preparation database, selected/prepared
Parquet files, split manifests and split-ID CSVs, hold-out predictions, OMNeT++
flow-level predictions, and any other row-level derivative. Aggregate counts,
hashes, metrics, and tests are included.

Follow README Workflow 2 with the independently obtained 18 files. The scripts
accept `--source-root`, inventory, and output paths; no source edit or author
machine path is required. Validate the source hashes first, then require a
`valid` inventory and 31/31 preparation checks before training.
