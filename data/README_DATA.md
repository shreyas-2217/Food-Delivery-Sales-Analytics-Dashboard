# Dataset setup

The raw data file is not committed to git (it is large). To rebuild:

1. Place the Swiggy orders file in this folder as `SWIGGY DATA.txt`
   (tab-separated, no header; columns: State, City, OrderDate, DayOfWeek,
   Quarter, WeekNo, Restaurant, Area, Category, Item, VegType,
   Price, Rating, RatingCount).
2. Run `python -m src.data_prep --raw "data/SWIGGY DATA.txt"`.

This creates `data/retail.db` (table `orders`) and `data/cleaned_orders.csv`.
Both are git-ignored. For hosting, upload the cleaned CSV separately and
point the app at it; see the Deployment section in README.md.
