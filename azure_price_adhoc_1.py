#!/usr/bin/env python3
import requests
import json
from tabulate import tabulate 


def build_pricing_table(json_data, table_data):
    for item in json_data['Items']:

        meter = item['meterName']
        table_data.append([item['productName'],item['unitOfMeasure'],item['skuName'],item['retailPrice'],item['meterName']])
        
def main():
    table_data = []
    table_data.append(['Product Name', 'Unit of Measure', 'SKU Name','Retail Price', 'Meter Name'])
    
    api_url = "https://prices.azure.com/api/retail/prices?api-version=2021-10-01-preview"
    query = "serviceFamily  eq 'Databases' and armRegionName eq 'westus' and serviceName eq 'Azure Database for MySQL'"
    response = requests.get(api_url, params={'$filter': query})
    json_data = json.loads(response.text)
    
    build_pricing_table(json_data, table_data)
    nextPage = json_data['NextPageLink']
    
    while(nextPage):
        response = requests.get(nextPage)
        json_data = json.loads(response.text)
        nextPage = json_data['NextPageLink']
        build_pricing_table(json_data, table_data)

    print(tabulate(table_data, headers='firstrow', tablefmt='psql'))
    
if __name__ == "__main__":
    main()