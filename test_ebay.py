import cloudscraper

def test():
    scraper = cloudscraper.create_scraper()
    url = 'https://www.ebay.com/sch/i.html?_nkw=iphone+15&LH_ItemCondition=1000'
    r = scraper.get(url)
    print("Status Code:", r.status_code)
    print("Length:", len(r.text))
    if r.status_code == 200:
        print("Success! First 200 chars:")
        print(r.text[:200])

if __name__ == "__main__":
    test()
