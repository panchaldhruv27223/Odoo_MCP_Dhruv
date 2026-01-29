"""
Odoo XML-RPC client for MCP server integration
"""

import json
import os
import re
import socket
import urllib.parse
import sys
import http.client
import xmlrpc.client
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv


class OdooClient:
    """Client for interacting with Odoo via XML-RPC"""

    def __init__(
        self,
        url,
        db,
        username,
        password,
        timeout=10,
        verify_ssl=True,
    ):
        """
        Initialize the Odoo client with connection parameters

        Args:
            url: Odoo server URL (with or without protocol)
            db: Database name
            username: Login username
            password: Login password
            timeout: Connection timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        # Ensure URL has a protocol
        if not re.match(r"^https?://", url):
            url = f"http://{url}"

        # Remove trailing slash from URL if present
        url = url.rstrip("/")

        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None

        # Set timeout and SSL verification
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # Setup connections
        self._common = None
        self._models = None

        # Parse hostname for logging
        parsed_url = urllib.parse.urlparse(self.url)
        self.hostname = parsed_url.netloc

        # Connect
        self._connect()

    def _connect(self):
        """Initialize the XML-RPC connection and authenticate"""
        # Tạo transport với timeout phù hợp
        is_https = self.url.startswith("https://")
        transport = RedirectTransport(
            timeout=self.timeout, use_https=is_https, verify_ssl=self.verify_ssl
        )

        print(f"Connecting to Odoo at: {self.url}", file=os.sys.stderr)
        print(f"  Hostname: {self.hostname}", file=os.sys.stderr)
        print(
            f"  Timeout: {self.timeout}s, Verify SSL: {self.verify_ssl}",
            file=os.sys.stderr,
        )

        # Set up endpoints
        self._common = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/common", transport=transport
        )
        self._models = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/object", transport=transport
        )

        # Authenticate and retrieve the user ID
        print(
            f"Authenticating with database: {self.db}, username: {self.username}",
            file=os.sys.stderr,
        )
        try:
            print(
                f"Making request to {self.hostname}/xmlrpc/2/common (attempt 1)",
                file=os.sys.stderr,
            )
            self.uid = self._common.authenticate(
                self.db, self.username, self.password, {}
            )
            if not self.uid:
                raise ValueError("Authentication failed: Invalid username or password")
        except (socket.error, socket.timeout, ConnectionError, TimeoutError) as e:
            print(f"Connection error: {str(e)}", file=os.sys.stderr)
            raise ConnectionError(f"Failed to connect to Odoo server: {str(e)}")
        except Exception as e:
            print(f"Authentication error: {str(e)}", file=os.sys.stderr)
            raise ValueError(f"Failed to authenticate with Odoo: {str(e)}")


    ## the core Odoo pipe
    ## This is the only place where Odoo is actually called.
    ## Think of this as: Press any Odoo ORM button remotely.
    def _execute(self, model, method, *args, **kwargs):
        """Execute a method on an Odoo model"""
        
        print("MODEL :", model)
        print("METHOD:", method)
        print("ARGS  :", args)
        print("KWARGS:", kwargs)

        return self._models.execute_kw(
            self.db, self.uid, self.password, model, method, args, kwargs
        )

    def execute_method(self, model, method, *args, **kwargs):
        """
        Execute an arbitrary method on a model

        Args:
            model: The model name (e.g., 'res.partner')
            method: Method name to execute
            *args: Positional arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method

        Returns:
            Result of the method execution
        """
        return self._execute(model, method, *args, **kwargs)

    def get_models(self):
        """
        Get a list of all available models in the system

        Returns:
            Dictionary with:
            - model_names: Sorted list of model technical names
            - models_details: Dict mapping model name to info
            - error: Error message if failed

        Examples:
            >>> client = OdooClient(url, db, username, password)
            >>> models = client.get_models()
            >>> print(len(models))
            125
            >>> print(models[:5])
            ['res.partner', 'res.users', 'res.company', 'res.groups', 'ir.model']
        """
        try:
            # First search for model IDs
            model_ids = self.execute_method("ir.model", "search", [])

            if not model_ids:
                return {
                    "model_names": [],
                    "models_details": {},
                    "error": "No models found",
                }

            # Then read the model data with only the most basic fields
            # that are guaranteed to exist in all Odoo versions
            result = self.execute_method("ir.model", "read", model_ids, ["model", "name"])

            # Extract and sort model names alphabetically
            models = sorted([rec["model"] for rec in result])

            # For more detailed information, include the full records
            models_info = {
                "model_names": models,
                "models_details": {
                    rec["model"]: {"name": rec.get("name", "")} for rec in result
                },
            }

            return models_info
        
        except Exception as e:
            print(f"Error retrieving models: {str(e)}", file=os.sys.stderr)
            return {"model_names": [], "models_details": {}, "error": str(e)}



    def get_model_info(self, model_name):
        """
        Get information about a specific model

        Args:
            model_name: Name of the model (e.g., 'res.partner')

        Returns:
            Dictionary with model information or error

        Examples:
            >>> client = OdooClient(url, db, username, password)
            >>> info = client.get_model_info('res.partner')
            >>> print(info['name'])
            'Contact'
        """
        try:
            result = self.execute_method(
                "ir.model",
                "search_read",
                [("model", "=", model_name)],
                **{"fields": ["name", "model"]},
            )

            if not result:
                return {"error": f"Model {model_name} not found"}

            return result[0]
        
        except Exception as e:
            print(f"Error retrieving model info: {str(e)}", file=os.sys.stderr)
            return {"error": str(e)}

    def get_model_fields(self, model_name):
        """
        Get field definitions for a specific model

        Args:
            model_name: Name of the model (e.g., 'res.partner')

        Returns:
            Dictionary mapping field names to their definitions

        Examples:
            >>> client = OdooClient(url, db, username, password)
            >>> fields = client.get_model_fields('res.partner')
            >>> print(fields['name']['type'])
            'char'
        """
        try:
            fields = self.execute_method(model_name, "fields_get")
            return fields
        except Exception as e:
            print(f"Error retrieving fields: {str(e)}", file=os.sys.stderr)
            return {"error": str(e)}

    def search_read(
        self, model_name, domain, fields=None, offset=None, limit=None, order=None
    ):
        """
        Search for records and read their data in a single call

        Args:
            model_name: Name of the model (e.g., 'res.partner')
            domain: Search domain (e.g., [('is_company', '=', True)])
            fields: List of field names to return (None for all)
            offset: Number of records to skip
            limit: Maximum number of records to return
            order: Sorting criteria (e.g., 'name ASC, id DESC')

        Returns:
            List of dictionaries with the matching records

        Examples:
            >>> client = OdooClient(url, db, username, password)
            >>> records = client.search_read('res.partner', [('is_company', '=', True)], limit=5)
            >>> print(len(records))
            5
        """
        try:
            kwargs = {}
            if offset is not None:
                kwargs["offset"] = offset
            if fields is not None:
                kwargs["fields"] = fields
            if limit is not None:
                kwargs["limit"] = limit
            if order is not None:
                kwargs["order"] = order

            result = self.execute_method(model_name, "search_read", domain, **kwargs)
            return result
        except Exception as e:
            print(f"Error in search_read: {str(e)}", file=os.sys.stderr)
            return []

    def read_records(self, model_name, ids, fields=None):
        """
        Read data of records by IDs

        Args:
            model_name: Name of the model (e.g., 'res.partner')
            ids: List of record IDs to read
            fields: List of field names to return (None for all)

        Returns:
            List of dictionaries with the requested records

        Examples:
            >>> client = OdooClient(url, db, username, password)
            >>> records = client.read_records('res.partner', [1])
            >>> print(records[0]['name'])
            'YourCompany'
        """
        try:
            kwargs = {}
            if fields is not None:
                kwargs["fields"] = fields

            result = self.execute_method(model_name, "read", ids, kwargs)
            return result
        except Exception as e:
            print(f"Error reading records: {str(e)}", file=os.sys.stderr)
            return []

    def search(
        self,
        model_name: str,
        domain: List,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None
        ) -> List[int]:

        """
        Search for record IDs matching domain.
        
        Args:
            model_name: Model name
            domain: Search domain
            offset: Number of records to skip
            limit: Maximum records to return
            order: Sort order
            
        Returns:
            List of matching record IDs
        """
        kwargs = {"offset": offset}
        if limit is not None:
            kwargs["limit"] = limit
        if order is not None:
            kwargs["order"] = order
            
        return self.execute_method(model_name, "search", domain, **kwargs)


    def search_count(self, model_name: str, domain: List) -> int:
        """
        Count records matching domain.
        
        Args:
            model_name: Model name
            domain: Search domain
            
        Returns:
            Number of matching records
        """
        return self.execute_method(model_name, "search_count", domain)


    def name_search(
        self,
        model_name: str,
        name: str = "",
        args: Optional[List] = None,
        operator: str = "ilike",
        limit: int = 100
        ) -> List[tuple]:
        """
        Search by name with autocomplete-style matching.
        
        Args:
            model_name: Model name
            name: Name to search for
            args: Additional domain conditions
            operator: Comparison operator
            limit: Maximum results
            
        Returns:
            List of (id, name) tuples
        """
        return self._execute(
            model_name,
            "name_search",
            name=name,
            args=args or [],
            operator=operator,
            limit=limit
        )


        
class RedirectTransport(xmlrpc.client.Transport):
    """Transport that adds timeout, SSL verification, and redirect handling"""

    def __init__(
        self, timeout=10, use_https=True, verify_ssl=True, max_redirects=5, proxy=None
    ):
        super().__init__()
        self.timeout = timeout
        self.use_https = use_https
        self.verify_ssl = verify_ssl
        self.max_redirects = max_redirects
        self.proxy = proxy or os.environ.get("HTTP_PROXY")

        if use_https and not verify_ssl:
            import ssl

            self.context = ssl._create_unverified_context()

    def make_connection(self, host):
        if self.proxy:
            proxy_url = urllib.parse.urlparse(self.proxy)
            connection = http.client.HTTPConnection(
                proxy_url.hostname, proxy_url.port, timeout=self.timeout
            )
            connection.set_tunnel(host)
        else:
            if self.use_https and not self.verify_ssl:
                connection = http.client.HTTPSConnection(
                    host, timeout=self.timeout, context=self.context
                )
            else:
                if self.use_https:
                    connection = http.client.HTTPSConnection(host, timeout=self.timeout)
                else:
                    connection = http.client.HTTPConnection(host, timeout=self.timeout)

        return connection

    def request(self, host, handler, request_body, verbose):
        """Send HTTP request with retry for redirects"""
        redirects = 0
        while redirects < self.max_redirects:
            try:
                print(f"Making request to {host}{handler}", file=os.sys.stderr)
                return super().request(host, handler, request_body, verbose)
            except xmlrpc.client.ProtocolError as err:
                if err.errcode in (301, 302, 303, 307, 308) and err.headers.get(
                    "location"
                ):
                    redirects += 1
                    location = err.headers.get("location")
                    parsed = urllib.parse.urlparse(location)
                    if parsed.netloc:
                        host = parsed.netloc
                    handler = parsed.path
                    if parsed.query:
                        handler += "?" + parsed.query
                else:
                    raise
            except Exception as e:
                print(f"Error during request: {str(e)}", file=os.sys.stderr)
                raise

        raise xmlrpc.client.ProtocolError(host + handler, 310, "Too many redirects", {})



def load_config():
    """
    Load Odoo configuration from environment variables or config file.
    
    Checks in order:
    1. Environment variables (ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)
    2. Config files:
       - ./odoo_config.json
       - ~/.config/odoo/config.json
       - ~/.odoo_config.json
    
    Returns:
        Configuration dictionary with url, db, username, password
        
    Raises:
        FileNotFoundError: If no configuration found
    """
    # Load .env file if exists
    load_dotenv()

    # Define config file paths to check
    config_paths = [
        "./odoo_config.json",
        os.path.expanduser("~/.config/odoo/config.json"),
        os.path.expanduser("~/.odoo_config.json"),
    ]

    # Try environment variables first
    env_vars = ["ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD"]
    if all(var in os.environ for var in env_vars):
        return {
            "url": os.environ["ODOO_URL"],
            "db": os.environ["ODOO_DB"],
            "username": os.environ["ODOO_USERNAME"],
            "password": os.environ["ODOO_PASSWORD"],
        }

    # Try to load from config files
    for path in config_paths:
        expanded_path = os.path.expanduser(path)
        if os.path.exists(expanded_path):
            print(f"Loading config from: {expanded_path}", file=sys.stderr)
            with open(expanded_path, "r") as f:
                return json.load(f)

    raise FileNotFoundError(
        "No Odoo configuration found.\n"
        "Please either:\n"
        "  1. Set environment variables: ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD\n"
        "  2. Create a config file at one of:\n"
        f"     - {config_paths[0]}\n"
        f"     - {config_paths[1]}\n"
        f"     - {config_paths[2]}"
    )

    

def get_odoo_client():
    """
    Get a configured Odoo client instance

    Returns:
        OdooClient: A configured Odoo client instance
    """
    config = load_config()

    # Get additional options from environment variables
    timeout = int(
        os.environ.get("ODOO_TIMEOUT", "30")
    )  # Increase default timeout to 30 seconds
    verify_ssl = os.environ.get("ODOO_VERIFY_SSL", "1").lower() in ["1", "true", "yes"]

    # Print detailed configuration
    print("Odoo client configuration:", file=os.sys.stderr)
    print(f"  URL: {config['url']}", file=os.sys.stderr)
    # print(f"  Database: {config['db']}", file=os.sys.stderr)
    # print(f"  Username: {config['username']}", file=os.sys.stderr)
    # print(f"  Timeout: {timeout}s", file=os.sys.stderr)
    # print(f"  Verify SSL: {verify_ssl}", file=os.sys.stderr)
    
    return OdooClient(
        url=config["url"],
        db=config["db"],
        username=config["username"],
        password=config["password"],
        timeout=timeout,
        verify_ssl=verify_ssl,
    )





## Methods that support writing 
### methods for writing also:    
#   def create(
    #     self,
    #     model_name: str,
    #     values: Union[Dict[str, Any], List[Dict[str, Any]]]
    # ) -> Union[int, List[int]]:
    #     """
    #     Create new record(s).
        
    #     Args:
    #         model_name: Model name
    #         values: Field values (dict or list of dicts)
            
    #     Returns:
    #         Created record ID(s)
    #     """
    #     return self._execute(model_name, "create", values)

    # def write(
    #     self,
    #     model_name: str,
    #     ids: List[int],
    #     values: Dict[str, Any]
    # ) -> bool:
    #     """
    #     Update existing records.
        
    #     Args:
    #         model_name: Model name
    #         ids: Record IDs to update
    #         values: Field values to set
            
    #     Returns:
    #         True if successful
    #     """
    #     return self._execute(model_name, "write", ids, values)

    # def unlink(self, model_name: str, ids: List[int]) -> bool:
    #     """
    #     Delete records.
        
    #     Args:
    #         model_name: Model name
    #         ids: Record IDs to delete
            
    #     Returns:
    #         True if successful
    #     """
    #     return self._execute(model_name, "unlink", ids)