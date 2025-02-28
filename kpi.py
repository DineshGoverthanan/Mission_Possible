from py_jama_rest_client.client import JamaClient
import pandas as pd
import os

# Function to extract unique 'assignedTo', 'modifiedBy', and 'createdBy' IDs and return them as a dictionary with names
def get_user_data(items,user_dict):
    # Use a set to collect unique user IDs
    user_ids = set()

    for item in items:
        # Extract IDs
        assigned_to = dictionary_finder(item, "assignedTo")
        modified_by = dictionary_finder(item, "modifiedBy")
        created_by = dictionary_finder(item, "createdBy")

        # Add IDs to the set if they are not None
        if assigned_to:
            user_ids.add(assigned_to)
        if modified_by:
            user_ids.add(modified_by)
        if created_by:
            user_ids.add(created_by)

    # Dictionary to store user information

    # Fetch user information for each unique ID
    for user_id in user_ids:
        try:
            user_info = client.get_user(user_id)
            if user_info:
                user_dict[user_id] = user_info.get("firstName", "Unknown")  # Use "Unknown" if firstName is missing
        except Exception as e:
            print(f"Error fetching user info for ID {user_id}: {e}")

    return user_dict

# Function to recursively find a key in dictionaries and lists
def dictionary_finder(dictionary, key_to_find):
    if isinstance(dictionary, dict):
        if key_to_find in dictionary:
            return dictionary[key_to_find]
        for value in dictionary.values():
            if isinstance(value, (dict, list)):
                return_value = dictionary_finder(value, key_to_find)
                if return_value is not None:
                    return return_value
    elif isinstance(dictionary, list):
        for item in dictionary:
            return_value = dictionary_finder(item, key_to_find)
            if return_value is not None:
                return return_value
    return None

# Jama client setup
host_domain = "https://konerqm.jamacloud.com"
Testrun_filter_id = 6261
Defect_filter_id = 6017
client_ID = os.getenv("JAMA_CLIENT_ID")
client_Secret = os.getenv("JAMA_CLIENT_SECRET")
client = JamaClient(
    host_domain=host_domain,
    credentials=(client_ID, client_Secret),
    oauth=True,
)

# Get data from Jama filters for both test runs and defects
testrun_data = client.get_filter_results(Testrun_filter_id)
defect_data = client.get_filter_results(Defect_filter_id)
print("Filter Data Fetched Successfully..")

# Fetch user data for both test runs and defects
user_dict = {}  # Dictionary to store fetched user data
user_dict = get_user_data(testrun_data + defect_data, user_dict)

# Process test run data and defect data
Testrun_data = [
    (
        dictionary_finder(item, "documentKey"),
        user_dict.get(dictionary_finder(item, "assignedTo")),
        dictionary_finder(item, "executionDate")
    )
    for item in testrun_data
]

Defect_data = [
    (
        dictionary_finder(item, "documentKey"),
        user_dict.get(dictionary_finder(item, "createdBy"))
    )
    for item in defect_data
]

# Modify kp_data to include unique days counted from execution dates
kp_data = {}
for item in Testrun_data + Defect_data:
    user = item[1]
    if user not in kp_data:
        kp_data[user] = {"defect_count": 0, "testrun_count": 0, "Days": set()}  # Using set to track unique days

    if item in Testrun_data:
        kp_data[user]["testrun_count"] += 1
        # Store execution date as string in Days set
        execution_date = item[2] if len(item) > 2 else None  # Execution date is stored at index 2
        if execution_date:
            kp_data[user]["Days"].add(execution_date)  # Add unique date strings to the set

    if item in Defect_data:
        kp_data[user]["defect_count"] += 1

# After collecting unique days, convert the set to the number of days
for user in kp_data:
    kp_data[user]["Days"] = len(kp_data[user]["Days"])  # Convert set of dates to the count of unique days

# Prepare to output data
output_data = []  # Initialize this list to store final KPI data
for user, data in kp_data.items():
    output_data.append({
        "User": user,
        "Testrun_count": data["testrun_count"],
        "Defect_count": data["defect_count"],
        "Days": data["Days"],
        "Test case Productivity": round(data["testrun_count"] / max(data["Days"], 1), 2),  # Avoid division by zero
        "Defect Observation Rate": round(data["defect_count"] / max(data["testrun_count"], 1), 2),
    })

# Convert data to pandas DataFrame for the KPI data
df_kp = pd.DataFrame(output_data)

# Extract defect data for CSV
defect_extracted_data = []
for item in defect_data:
    fields = item.get("fields", {})
    defect_extracted_data.append({
        "Document Key": fields.get("documentKey"),
        "Name": fields.get("name"),
        "Created By": user_dict.get(fields.get("createdBy")),
        "Found in Build": fields.get("BUG_foundInBuild$154"),
        "Found On Date": fields.get("BUG_foundOnDate$154"),
    })

df_defects = pd.DataFrame(defect_extracted_data)

# Extract test run data for CSV
testrun_extracted_data = []
for item in testrun_data:
    fields = item.get("fields", {})
    testrun_extracted_data.append({
        "TestRunStatus": fields.get("testRunStatus"),
        "ExecutionDate": fields.get("executionDate"),
        "Document Key": fields.get("documentKey"),
        "Name": fields.get("name"),
        "Assigned To": user_dict.get(fields.get("assignedTo")),


    })

df_testruns = pd.DataFrame(testrun_extracted_data)

# Export the dataframes to CSV files
df_kp.to_csv("kp_data.csv", index=False)  # KPI data
df_defects.to_csv("defect_data.csv", index=False)  # Defect data
df_testruns.to_json("testrun_data.json", orient="records", indent=4)
print("Data exported to CSV files: kp_data.csv, defect_data.csv, testrun_data.json")
"""
# Export the dataframes to an Excel file with multiple sheets
output_file = "kp_data.xlsx"
with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    df_kp.to_excel(writer, sheet_name='KP', index=False)
    df_defects.to_excel(writer, sheet_name='Defect', index=False)
    df_testruns.to_excel(writer, sheet_name='Test run', index=False)

print(f"Data exported to {output_file}")
"""
