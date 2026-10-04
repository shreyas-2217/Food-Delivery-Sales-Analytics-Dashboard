# Dataset setup

The raw data file is not committed to git (it is large). To rebuild:

1. Place the Swiggy orders file in this folder as `SWIGGY DATA.txt`
   (tab-separated, no header; columns: State, City, OrderDate, DayOfWeek,
   Quarter, WeekNo, Restaurant, Area, Category, Item, VegType,
   Price, Rating, RatingCount).
2. Run `python -m src.data_prep --raw "data/SWIGGY DATA.txt"`.

This creates `data/retail.db` (table `orders`) for local use.
Both the raw file and the database are git-ignored. For hosting, the repo
includes the committed `data/cleaned_orders_sample.csv`, which the app
builds the database from automatically on startup.
