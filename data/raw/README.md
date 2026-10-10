# Raw data (not committed)

**Online Retail II**: UCI Machine Learning Repository, Daqing Chen (2019), licence CC BY 4.0.
https://archive.ics.uci.edu/dataset/502/online+retail+ii

Download it with:

```bash
python -m src.download_data
```

This saves `online_retail_II.xlsx` here (≈45 MB, two sheets: *Year 2009-2010* and
*Year 2010-2011*). The loader also accepts the binary `.xlsb` version.

You don't need the raw file to explore the project: the cleaned star schema is already
committed in `data/processed/`.
