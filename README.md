# zAgent
Bob_the_builderthon

Our goal is to get a website that can scrape the internet to find discounts on travel tickets. We plan on making a website that will show all opportunities for students to grab some discounts.

website: UI/UX and Javascript (take in a user's name, budget, how frequently the want SMS,phone #/email,destination, age): 3 categories: cheapest,fastest, reccomended,budget

Scraping for discounts: skyscanner,travekpayout,airbnb, scraping news website (travel advisories)

Database:gives all options

Claude: gives best option, identify landmarks and choose options


Plan
1. User input:
   - Name
   - Status
       - Student
       - Senior
       - ...
   - Location
   - Destination
   - Date of travel
   - Prefered travel method
   - Stay: Hotel / Airbnb
   - Estimate Budget
2. Data Processing:
   -Scrapes through website on major travel website to find the best deals.
   - Use data in our database and Claude API to determine the best option for the user
4. Output:
   - Most Recommended way
   - Cheapest way
   - Fastest way
   - News related to traveling to that place
5. Purchase
   - Redirect them to the official website with discounts to purchase
