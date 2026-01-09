from dotenv import load_dotenv
from src.odoo_client import get_odoo_client

def main():
    
    odoo = get_odoo_client()
    
    # print(odoo)
    
    # all_models = odoo.get_models()
    # # print(all_models)
    # # print(all_models["model_names"])
    # all_models_name = all_models["model_names"]
    
    # with open("odoo_model.txt", "w") as odoo_model_file:
        
    # uniques_models = set()
    
    # for i in all_models_name:
    #     # print(i)
    #     first = i.split(".")[0]
    #     if first not in uniques_models:
    #         uniques_models.add(first)

    # uniques_models = sorted(list(uniques_models))
    # # print(uniques_models)
    # for i in uniques_models:
    #     print(i)
    
    
    # payments = odoo.execute_method(
    #         "account.payment", 
    #         "search_read",
    #         [], # Empty domain = Get All Records
    #         ["id", "date", "payment_type", "state", "company_id", "amount"],
    #         limit=5,
    #         order="date desc" # Get the newest ones
    #     )
    
    # print(payments)
    


if __name__ == "__main__":
    
    main()