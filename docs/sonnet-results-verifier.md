# Sonnet-2 results verifier / Verifier hasil Sonnet-2

## ID

`sonnet_results_verifier.py` memverifikasi paket hasil resmi Sonnet-2 secara **offline dan read-only**, lalu melakukan lookup exact DID tanpa mencetak DID tersebut. Sumber dipin ke commit resmi `195647a4d85733ecd4862d67dc7bf7a62e673c58` dan pengumuman @flop_labs tanggal `2026-09-23T01:58:58Z`:

- https://x.com/flop_labs/status/2102578439643693562
- https://github.com/flop-labs/technocore-sonnet-challenge/tree/195647a4d85733ecd4862d67dc7bf7a62e673c58/results/sonnet-2

Verifier mengecek hash source record dan manifest, 6.856 DID, total alokasi 97.964 FLOP, konsistensi `allocations.csv` ↔ `payouts.json` ↔ settlement receipt, role/count/amount, finalists, dan winning vote total. Fixture resmi disimpan byte-for-byte. Negative fixture mendefinisikan tamper hash, payout, allocation, dan commit yang wajib ditolak.

Lookup primary DID saat verifikasi rilis menghasilkan `NOT_LISTED`. Tool tidak mencetak DID input. Ini bukan saldo nol atau penolakan global; artinya exact DID itu tidak ada dalam paket alokasi Sonnet-2 yang dipin.

State tidak boleh dilompati:

`allocated → claimable → claimed → paid`

- `allocated`: hanya `LISTED` atau `NOT_LISTED` dari exact-DID lookup.
- `claimable`: `UNVERIFIED`; paket hanya bilang claim dibuka saat mainnet live.
- `claimed`: `UNVERIFIED`; perlu receipt claim exact DID.
- `paid`: `UNVERIFIED`; allocation bukan transfer.

Dua artifact yang disebut manifest—`allocations.json` dan closed `referee.sqlite`—tidak tersedia di tree resmi ini. Karena itu full independent ledger replay belum diklaim. Ya, JSON besar masih bukan mesin waktu.

## EN

The verifier validates the commit-pinned official package offline, cross-checks its available manifest artifacts, and performs an exact-DID lookup without echoing the queried identity. A listed allocation does not prove that claims are open, a claim was submitted, or payment occurred. Those states remain separately `UNVERIFIED` until authoritative exact-DID receipts exist.

## Usage

```sh
python3 sonnet_results_verifier.py \
  evidence/fixtures/sonnet-2-official \
  --source-record evidence/sonnet-2-source.json \
  --did 'did:key:<exact-public-did>'
```

The implementation has no network import, POST, private-key loader, signing call, wallet, transaction, claim, or write path. It only reads operator-supplied local files and prints public verification facts.
