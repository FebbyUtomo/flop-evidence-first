# Evidence-first FLOP tooling — bilingual tutorial

Repositori ini berisi dua validator offline dan satu monitor online read-only untuk membuktikan klaim tentang Technocore dan jaringan FLOP. Tutorial ini menunjukkan cara menjalankan semuanya dalam beberapa menit — tanpa private key, tanpa wallet, tanpa network write.

This repository ships two offline validators and one read-only online monitor that verify claims about Technocore and the FLOP network. This tutorial runs all of them in a few minutes — no private keys, no wallets, no network writes.

## Yang dibutuhkan / Prerequisites

- Python 3.11+
- `git`
- Koneksi internet dibutuhkan untuk clone, pemeriksaan Arcscan opsional, dan monitor kriteria resmi. Validator receipt dan lifecycle berjalan offline.
- Internet is required for cloning, the optional Arcscan check, and the official-criteria monitor. The receipt and lifecycle validators run offline.

## 1 — Verifikasi receipt Technocore / Verify a Technocore receipt

Technocore menandatangani pesan dengan skema `room|nonce|text`. Verifikator memeriksa bytes persisnya terhadap DID yang dipin.

Technocore signs messages with the `room|nonce|text` scheme. The verifier checks the exact bytes against a pinned DID.

```bash
git clone https://github.com/FebbyUtomo/flop-evidence-first.git
cd flop-evidence-first

# positive case — should exit 0
python3 receipt_verifier.py \
  evidence/fixtures/technocore-valid.json \
  --did did:key:z6MkgjQRmahVjPgCBdoHDPEoUwAMG2KisqjoNDMiH1B68Wcs

# negative cases — every one must exit 1
python3 receipt_verifier.py evidence/fixtures/technocore-invalid-text.json     --did did:key:z6MkgjQRmahVjPgCBdoHDPEoUwAMG2KisqjoNDMiH1B68Wcs
python3 receipt_verifier.py evidence/fixtures/technocore-invalid-signature.json --did did:key:z6MkgjQRmahVjPgCBdoHDPEoUwAMG2KisqjoNDMiH1B68Wcs
python3 receipt_verifier.py evidence/fixtures/technocore-wrong-signer.json     --did did:key:z6MkgjQRmahVjPgCBdoHDPEoUwAMG2KisqjoNDMiH1B68Wcs
```

Yang harus kamu lihat / What you should see: `{"verified":true,...}` untuk fixture valid, `receipt_invalid:...` untuk tiga sisanya.

## 2 — Validasi lifecycle testnet Flipt / Validate the Flipt testnet lifecycle

Enam transaksi Arc Testnet publik membuktikan satu siklus lengkap: graduation → unbond → release (90 detik) → liquidity → Auto-Sell → filled.

Six public Arc Testnet transactions prove one full cycle: graduation → unbond → release (90 seconds) → liquidity → Auto-Sell → filled.

```bash
python3 flipt_lifecycle.py evidence/fixtures/flipt-lifecycle-valid.json

# read one source yourself — each fixture URL is a live Arcscan record
curl -s https://api-testnet.arc-scan.org/v1/txs/0x382e36151a6803eed28af47c904e4b998719c7a8cf1e88e306c46cdb117246a7 | head -c 400
```

Hasil sukses mencantumkan `final_state:auto_sell_filled` dan `minimum_maturity_seconds:90`.

## 3 — Pantau kriteria resmi FLOP / Watch official FLOP criteria

Monitor membandingkan snapshot terhadap lima halaman draft resmi flop.finance, dan menyimpan dua konflik draft yang belum terselesaikan alih-alih memilih angka yang enak.

The monitor compares its snapshot against five official flop.finance draft pages and preserves two unresolved draft conflicts instead of picking the nicer number.

```bash
python3 criteria_monitor.py --manifest evidence/official-criteria.json
# exit 0 = unchanged, 2 = content drift, 3 = material marker lost
```

## 4 — Jalankan seluruh test suite / Run the whole test suite

```bash
python3 -m unittest discover -s tests -p 'test_*.py'   # 57 tests
python3 -O -m unittest discover -s tests -p 'test_*.py' # adversarial: assertions removed
python3 scripts/verify_roadmap.py                       # ledger integrity
```

Suite includes tampered-signature, replayed-transcript, fabricated-calldata, fractional-maturity, and injected-credential mutations. Semuanya harus ditolak.

## Apa yang TIDAK dibuktikan / What this does NOT prove

Verifikasi ini membuktikan **keaslian dan integritas** — bukan nilai, bukan alokasi.

These checks prove **authenticity and integrity** — not value, not allocation.

- signature valid ≠ pekerjaan berguna / a valid signature ≠ useful work;
- transaksi testnet ≠ kelayakan airdrop / a testnet transaction ≠ airdrop eligibility;
- skor roadmap ≠ janji alokasi $FLOP / a roadmap score ≠ a promised $FLOP allocation.

Official eligibility/allocation/payment: **UNVERIFIED** sampai ada receipt resmi exact-identity. Sampai jumpa di bukti berikutnya.

## Lisensi / License

Report text: CC BY 4.0 · Code: MIT · Private identity material: excluded, not licensed.
