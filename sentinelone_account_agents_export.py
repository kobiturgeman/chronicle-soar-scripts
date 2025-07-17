from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
import requests
import csv
from io import StringIO
import datetime

@output_handler
def main():
    siemplify = SiemplifyAction()

    api_key = siemplify.extract_action_param(
        param_name="API Key",
        default_value=None,
        input_type=str,
        is_mandatory=True,
        print_value=False  # Set to True if you want to log the API key
    )
    base_url = siemplify.extract_action_param(
        param_name="Base URL",
        default_value=None,
        input_type=str,
        is_mandatory=True,
        print_value=False
    )
    # Initialize result variables
    status = EXECUTION_STATE_COMPLETED
    output_message = "Successfully extracted account names and active agent counts."
    result_value = ""

    try:
        # Step 1: Export accounts and get account names
        export_endpoint = f"{base_url}/web/api/v2.1/export/accounts"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        export_response = requests.get(export_endpoint, headers=headers)
        export_response.raise_for_status()

        # Parse the CSV content
        csv_data = StringIO(export_response.text)
        reader = csv.DictReader(csv_data)

        # Extract account names
        account_names = [row["Account Name"] for row in reader if "Account Name" in row]

        if not account_names:
            output_message = "No account names found in the export."
            result_value = ""
            siemplify.end(output_message, result_value, status)
            return

        # Step 2: Retrieve details and collect active agents
        account_data = []
        accounts_endpoint = f"{base_url}/web/api/v2.1/accounts"

        for name in account_names:
            params = {"name": name}
            account_response = requests.get(accounts_endpoint, headers=headers, params=params)
            account_response.raise_for_status()

            data = account_response.json().get("data", [])
            if data:
                account_details = data[0]  # Assuming account names are unique
                active_agents = account_details.get("activeAgents", 0)
                account_data.append((name, active_agents))
            else:
                siemplify.LOGGER.info(f"No account found with name: {name}")

        if not account_data:
            output_message = "No valid account data found."
            result_value = ""
            siemplify.end(output_message, result_value, status)
            return

        # Step 3: Write to CSV with date
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        csv_filename = f"/tmp/accountsS1_{current_date}.csv"  # Updated filename with date
        header = ['Account Name', 'Active Agents']

        with open(csv_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            writer.writerows(account_data)

        siemplify.LOGGER.info(f"Data successfully written to {csv_filename}")
        result_value = csv_filename  # Set result_value to the filename

        # Optionally, attach the CSV file to the action result
        with open(csv_filename, 'r') as file:
            csv_content = file.read()
            siemplify.result.add_attachment(f"accountsS1_{current_date}.csv", "text/csv", csv_content)

    except requests.exceptions.RequestException as e:
        siemplify.LOGGER.error(f"Error occurred during API requests: {e}")
        output_message = f"Failed to retrieve account data: {e}"
        status = EXECUTION_STATE_FAILED
        result_value = ""
    except Exception as e:
        siemplify.LOGGER.error(f"An unexpected error occurred: {e}")
        output_message = f"An unexpected error occurred: {e}"
        status = EXECUTION_STATE_FAILED
        result_value = ""

    siemplify.end(output_message, result_value, status)

if __name__ == "__main__":
    main()
