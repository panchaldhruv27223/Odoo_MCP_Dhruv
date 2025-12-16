from src.odoo_client import get_odoo_client
from dotenv import load_dotenv

load_dotenv()

def main():
    my_odoo_client = get_odoo_client()
    # print(my_odoo_client.uid)
    # print(my_odoo_client)
    
    # models = my_odoo_client.get_models()
    
    # print(f"Models type: {type(models)}")
    # print(f"Total Key in the models : {models.keys()}")
    
    # print(f"Total Models are: {len(models)}")
    ## Output : --
                # 2
                
    ## Output : -- Total Key in the models : dict_keys(['model_names', 'models_details'])
    
    # models_name = models["model_names"]
    # models_details = models["models_details"]
    
    # print(f"Type of Models Name : {type(models_name)}")
    # print(f"Type of Models details : {type(models_details)}")

    # print(f"Total Models name are : {len(models_name)}")  
    # print(f"Total Models details are : {len(models_details)}")     
    
    ## Output : --
                # Type of Models Name : <class 'list'>
                # Type of Models details : <class 'dict'>
                # Total Models name are : 815
                # Total Models details are : 815   
    
    
    ## FIRST 20 models name:
    
    # for i in models_name[:20]:
    #     print(i)
    
    ## Output : --
                # _unknown
                # account.account
                # account.account.tag
                # account.accrued.orders.wizard
                # account.aged.partner.balance.report.handler
                # account.aged.payable.report.handler
                # account.aged.receivable.report.handler
                # account.analytic.account
                # account.analytic.applicability
                # account.analytic.distribution.model
                # account.analytic.line
                # account.analytic.plan
                # account.asset
                # account.asset.group
                # account.asset.report.handler
                # account.auto.reconcile.wizard
                # account.automatic.entry.wizard
                # account.autopost.bills.wizard
                # account.avatax.unique.code
                # account.balance.sheet.report.handler
    
    # print(models_details)
    # {'account.account': {'name': 'Account'}, 'account.analytic.account': {'name': 'Analytic Account'}, 'account.asset': {'name': 'Asset/Revenue Recognition'}, 'res.partner.bank': {'name': 'Bank Accounts'}, 'account.online.link': {'name': 'Bank Connection'}, 'account.bank.statement': {'name': 'Bank Statement'}, 'extract.mixin': {'name': 'Base class to extract data from documents'}, 'account.batch.payment': {'name': 'Batch Payment'}, 'stock.picking.batch': {'name': 'Batch Transfer'}, 'blog.blog': {'name': 'Blog'}, 'blog.post': {'name': 'Blog Post'}, 'budget.analytic': {'name': 'Budget'}, 'calendar.event': {'name': 'Calendar Event'}, 'res.company': {'name': 'Companies'}, 'res.partner': {'name': 'Contact'}, 'hr.department': {'name': 'Department'}, 'discuss.channel': {'name': 'Discussion Channel'}, 'documents.document': {'name': 'Document'}, 'mail.thread.cc': {'name': 'Email CC management'}, 'mail.thread': {'name': 'Email Thread'}, 'hr.employee': {'name': 'Employee'}, 'hr.contract': {'name': 'Employee Contract'}, 'l10n_in.gst.return.period': {'name': 'GST Return Period'}, 'iap.account': {'name': 'IAP Account'}, 'hr.job': {'name': 'Job Position'}, .......
    
    
    ## suppose the model name is : res.partner
    
    # info = my_odoo_client.get_model_info('res.partner')
    # print(info)
        
        ### output ----
        # Making request to staging.bharat.tools/xmlrpc/2/object
        # {'id': 87, 'name': 'Contact', 'model': 'res.partner'}
    
    
    
    # model_field_info = my_odoo_client.get_model_fields('res.partner')
    
    # print(f"model field type: {type(model_field_info)}")
    # print(f"model total keys: {len(model_field_info.keys())}")
    ## Output : --
            # model field type: <class 'dict'>
            # model total keys: 241
            
    # for name, meta in list(model_field_info.items())[:10]:
    #     print(name, "→", meta["type"])

        # avatax_unique_code → char
        # is_seo_optimized → boolean
        # website_meta_title → char
        # website_meta_description → text
        # website_meta_keywords → char
        # website_meta_og_img → char
        # seo_name → char
        # website_id → many2one
        # website_published → boolean
        # is_published → boolean
    
    
    
    
    # records = my_odoo_client.search_read(
    #                                         "res.partner",
    #                                         domain=[("is_company", "=", True)],
    #                                         fields=["id", "name", "email"],
    #                                         limit=5
    #                                         )
    # for r in records:
    #     print(r)
    
    ## Output --- 
    
    # Making request to staging.bharat.tools/xmlrpc/2/object
    # {'id': 3049, 'name': '(SHD) ShivHarDHA Projects', 'email': False}
    # {'id': 2621, 'name': 'A ENTERPRISE', 'email': False}
    # {'id': 2393, 'name': 'A-ONE ENTERPRISE', 'email': False}
    # {'id': 2682, 'name': 'A.K.PANCHAL', 'email': False}
    # {'id': 1438, 'name': 'AAKAR SALES AND SERVICE', 'email': False}




    # result = my_odoo_client.execute_method(
    #     "res.partner",
    #     "search_count",
    #     [("is_company", "=", True)]
    # )
    # print("Company count:", result)


    # Company count: 966
    
    
    # recordes_result = my_odoo_client.read_records(
                                                
    #                                             "res.partner",
    #                                             [1]
                                                
    #                                             )
    
    # print(recordes_result)
    
    
if __name__ == "__main__":
    main()