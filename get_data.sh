mkdir raw_data

# Adult Census
wget https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data
wget https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.test
wget https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.names
mkdir raw_data/adult
mv adult.* raw_data/adult/

# Bank Marketting
wget https://archive.ics.uci.edu/ml/machine-learning-databases/00222/bank-additional.zip
mkdir raw_data/bank_marketing
mv bank-additional.zip raw_data/bank_marketing
cd raw_data/bank_marketing
unzip bank-additional.zip
mv bank-additional/* .
rm -r -f bank-additional/
cd ~/Projects/tabulardl-benchmark/

kaggle datasets download -d janiobachmann/bank-marketing-dataset
mkdir raw_data/bank_marketing_kaggle
mv bank-marketing-dataset.zip raw_data/bank_marketing_kaggle
cd raw_data/bank_marketing_kaggle
unzip bank-marketing-dataset.zip
cd ~/Projects/tabulardl-benchmark/

# you need the Kaggle API installation: https://github.com/Kaggle/kaggle-api
# SF Crime
kaggle competitions download -c sf-crime
mkdir raw_data/sf_crime
mv sf-crime.zip raw_data/sf_crime
cd raw_data/sf_crime
unzip sf-crime.zip
cd ~/Projects/tabulardl-benchmark/

# Ponpare Coupons
kaggle competitions download -c coupon-purchase-prediction
mkdir raw_data/ponpare
mv coupon-purchase-prediction.zip raw_data/ponpare
cd raw_data/ponpare
unzip coupon-purchase-prediction.zip
mkdir zip_files
mv *.zip zip_files
cd zip_files
find . -name "*.zip" | while read filename; do unzip -o -d "`dirname "$filename"`" "$filename"; done;
cd ..
mv zip_files/*.csv .
mv zip_files/documentation .
cd ~/Projects/tabulardl-benchmark/

# Airbnb listings
wget http://data.insideairbnb.com/united-kingdom/england/london/2021-02-09/data/listings.csv.gz
mkdir raw_data/airbnb
mv listings.csv.gz raw_data/airbnb

# NYC Taxi Trip Duration
kaggle competitions download -c nyc-taxi-trip-duration
mkdir raw_data/nyc_taxi
mv nyc-taxi-trip-duration.zip raw_data/nyc_taxi
cd raw_data/nyc_taxi
unzip nyc-taxi-trip-duration.zip
cd ~/Projects/tabulardl-benchmark/


