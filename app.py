import discord
from discord.ext import commands
import urllib.request
from bs4 import BeautifulSoup
import asyncio

bot = commands.Bot(command_prefix=".", intents=discord.Intents.all())


def fetch_product_info(url):
    try:
        response = urllib.request.urlopen(url)
        content = response.read()
        soup = BeautifulSoup(content, "html.parser")

        products = []

        # Extract product details
        product_blocks = soup.find_all("div", class_="s-result-item")
        for block in product_blocks:
            title = block.find("span", class_="a-size-base-plus a-color-base a-text-normal")
            price = block.find("span", class_="a-offscreen")
            link = block.find("a", class_="a-link-normal s-no-outline")
            rrp_span = block.find("span", class_="a-size-base a-color-secondary")
            image = block.find("img", class_="s-image")

            if title and price and link and image:
                title = title.get_text().strip()
                price = float(price.get_text().replace("£", "").replace(",", ""))  # Convert price to float
                link = "https://www.amazon.co.uk" + link['href']
                product_code = link[-10:]  # Get the last 10 characters as the product code

                rrp = None
                if rrp_span:
                    rrp_parent = rrp_span.parent
                    rrp = rrp_parent.find("span", class_="a-price a-text-price")
                    if rrp:
                        rrp = rrp.get_text().replace("£", "").replace(",", "").split()[0]
                        rrp = float(rrp[:-5])  # Remove the last 5 characters and convert to float

                image_link = image['src']  # Get the image link

                products.append({
                    "title": title,
                    "price": price,
                    "rrp": rrp,
                    "link": link,
                    "product_code": product_code,
                    "image_link": image_link
                })

        return products

    except urllib.error.URLError as e:
        print(f"Error occurred while fetching the website: {e}")
        return None

def get_channel_id(search_url, discount_percentage):
    # Define the mapping of search URLs and their corresponding channel IDs
    url_to_channel_map = {
        "https://www.amazon.co.uk/s?k=tech&rh=n%3A429892031&ref=nb_sb_noss": {
            20: 1132317350734073856,
            40: 1132317381239255150,
            60: 1132317416521728170,
            80: 1132317434473353276,
        },
        "https://www.amazon.co.uk/s?k=clothing&ref=nb_sb_noss": {
            20: 1132317461639864320,
            40: 1132317477225889852,
            60: 1132317497769590794,
            80: 1132317516799160360,
        },
        "https://www.amazon.co.uk/s?k=video+games&crid=2RVKD0E9LPKER&sprefix=video+game%2Caps%2C198&ref=nb_sb_noss_2": {
            20: 1132317536004870207,
            40: 1132317550315831377,
            60: 1132317565243375696,
            80: 1132317588274294784,
        }
    }

    # Find the closest discount range
    discount_ranges = sorted(url_to_channel_map[search_url].keys())
    closest_range = min(discount_ranges, key=lambda x: abs(x - discount_percentage))

    # Return the corresponding channel ID
    return url_to_channel_map[search_url][closest_range]

@bot.event
async def on_ready():
    print('Bot online')
    # Start scanning and sending the products with more than 50% discount to the specified channel
    await scan_and_send_discounted_products()

async def scan_and_send_discounted_products():
    urls_to_fetch = [
        "https://www.amazon.co.uk/s?k=tech&rh=n%3A429892031&ref=nb_sb_noss",
        "https://www.amazon.co.uk/s?k=clothing&ref=nb_sb_noss",
        "https://www.amazon.co.uk/s?k=video+games&crid=2RVKD0E9LPKER&sprefix=video+game%2Caps%2C198&ref=nb_sb_noss_2"
    ]

    sent_product_codes = []  # To store product codes of products already sent
    link_index = 0  # Index to keep track of the current link being used
    iteration_count = 0  # Counter to keep track of iterations

    while True:
        url_to_fetch = urls_to_fetch[link_index]

        products = fetch_product_info(url_to_fetch)

        if products:
            for product in products:
                product_code = product['product_code']
                discount_percentage = 100 - ((product['price'] / product['rrp']) * 100) if product['rrp'] else None

                if discount_percentage is not None and discount_percentage > 5 and product_code not in sent_product_codes:
                    # Get the corresponding channel ID based on the search URL and discount percentage
                    channel_id = get_channel_id(url_to_fetch, discount_percentage)

                    title = product['title']
                    price_euro = product['price'] * 1.15
                    rrp_euro = product['rrp'] * 1.15 if product['rrp'] is not None else None

                    if rrp_euro is not None:
                        rrp_str = f"€{rrp_euro:.2f}"
                    else:
                        rrp_str = "N/A"

                    image_link = product['image_link']

                    embed = discord.Embed(title=title, url=product['link'], description="", colour=discord.Colour.darker_grey())
                    embed.add_field(name="Product ID", value=product_code, inline=False)
                    embed.add_field(name="\n", value="\n", inline=False)
                    embed.add_field(name="Discounted Price", value=f"€{price_euro:.2f}", inline=False)
                    embed.add_field(name="\n", value="\n", inline=False)
                    embed.add_field(name="Retail Price", value=rrp_str, inline=False)
                    embed.add_field(name="\n", value="\n", inline=False)
                    embed.add_field(name="Discount Percentage", value=f"{discount_percentage:.2f}%", inline=False)
                    embed.set_thumbnail(url=image_link)

                    channel = bot.get_channel(channel_id)
                    await channel.send(embed=embed)

                    # Add the product code to the set of sent product codes
                    sent_product_codes.append(product_code)

        iteration_count += 1

        # After every fifth iteration, swap the link index and reset the iteration count
        if iteration_count % 5 == 0:
            link_index = (link_index + 1) % len(urls_to_fetch)
            iteration_count = 0

            # Pause for 4 minutes and 2 seconds before scanning the page again
            await asyncio.sleep(242)

bot.run("MTEzMDg2OTg5NjI5MzY1MDQ2Mg.G-fdb8.w1qaXmAHtKIyIM4UrnwT2iuVPJS2JJTNcPjUZE")
