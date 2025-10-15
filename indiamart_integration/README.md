# Odoo 19 - IndiaMART Integration

This module provides a complete integration with the IndiaMART Pull API for Odoo 19 Community Edition. It automates the process of fetching new business inquiries from your IndiaMART seller account and creating them as clean, enriched leads in your Odoo CRM.

This project was built to be a robust, standalone solution for businesses looking to streamline their lead capture process from one of India's largest B2B marketplaces.

## Key Features

* **Automated Lead Sync:** A scheduled action runs every 5 minutes to automatically pull the latest leads from IndiaMART.
* **Manual Fetching:** A user-friendly wizard allows you to import leads from any specific 7-day period in the past.
* **Detailed Lead Creation:** Creates new inquiries as **Leads** (not Opportunities), allowing for a proper sales qualification workflow within the Odoo CRM.
* **Lead Enrichment:**
    * Automatically assigns an initial **Probability** based on the type of inquiry (e.g., Direct Call, Buy-Lead, WhatsApp).
    * Maps detailed information including Company Name, Full Address, Contact Info, and the specific product of interest.
    * Stores the original IndiaMART Lead Type (Direct Enquiry, PNS Call, etc.) on the lead form for clarity.
* **API Call Logging:** A dedicated menu in the Odoo UI allows you to view the history and status of every API call made, both manual and automated, making monitoring and debugging simple.
* **Duplicate Prevention:** Uses IndiaMART's unique query ID to ensure no duplicate leads are ever created in your system.

## Installation

You can install this module using either the standard method or with Docker.

#### Standard Installation
1.  Download this repository.
2.  Place the `indiamart_integration` folder into your Odoo `addons` directory.
3.  Restart your Odoo server.
4.  Navigate to the **Apps** menu in Odoo.
5.  Click **Update Apps List** (Developer Mode must be active).
6.  Search for "IndiaMART Integration" and click **Install**.

#### Docker Installation
1.  Place the `indiamart_integration` folder into your `custom-addons` directory.
2.  Add the following line to your `Dockerfile`:
    ```dockerfile
    COPY ./custom-addons/indiamart_integration /mnt/extra-addons/indiamart_integration
    ```
3.  Rebuild your Docker image and restart the containers:
    ```bash
    docker-compose up -d --build
    ```
4.  Once the container is running, install the module from the Odoo Apps menu as described above.

## Configuration

After installation, you must configure your API key.

1.  Navigate to the **IndiaMART** menu in Odoo.
2.  Go to the **Configuration** sub-menu.
3.  Enter your **IndiaMART API Key** obtained from the IndiaMART Seller Panel.
4.  Click the **"Test Connection"** button to verify that your key is correct and the API is reachable.

![Configuration Screen](https://i.imgur.com/your-screenshot-url.png) ## Usage

Once configured, the module is fully automated.

* **Automated Leads:** New leads will automatically appear in your **CRM -> Leads** menu every 5 minutes.
* **Manual Fetching:** To get leads from a past period, go to **IndiaMART -> Fetch Leads**.
* **Monitoring:** To check the history of API calls, go to **IndiaMART -> API Logs**.

## License

This module is licensed under the General Public License. See the `LICENSE` file for full details.

## Author

* [Rohitkumar Singh]
