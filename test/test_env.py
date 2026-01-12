import os 
from dotenv import load_dotenv
load_dotenv(".env")

# print(os.environ)

print(os.environ["ODOO_URL"])
# print(os.environ.get("ODOO_DB"))