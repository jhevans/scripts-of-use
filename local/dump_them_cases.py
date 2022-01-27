import logging
import sys
import os
import csv
import json
import requests
import time

COURT_CASE_TOKEN = os.environ.get('COURT_CASE_TOKEN')
CHER_TOKEN = os.environ.get('CHER_TOKEN')
CCS_HOST = "https://court-case-service-preprod.apps.live-1.cloud-platform.service.justice.gov.uk"
CHER_HOST = "https://court-hearing-event-receiver-preprod.hmpps.service.justice.gov.uk"
PAC_HOST = "https://prepare-a-case-preprod.apps.live-1.cloud-platform.service.justice.gov.uk"
GET_CASE_TEMPLATE = f"{CCS_HOST}/case/%s/defendant/%s"
POST_HEARING_TEMPLATE = f"{CHER_HOST}/hearing/%s"
file_path = os.environ.get('FILE_PATH')
bad_json_path = "/Users/johnevans/temp/bad_json"
good_json_path = "/Users/johnevans/temp/good_json"
csv.field_size_limit(sys.maxsize)

resume_file_path = f"{file_path}-resume.txt"
failures_path = f"{file_path}-failures.csv"

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
file_handler = logging.FileHandler(f'{file_path}.log')
file_handler.setLevel(logging.DEBUG)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


resume_at = 0

def authenticate(client_id, client_secret):
    pass


def checkpoint(checkpoint):
    with open(resume_file_path, 'w') as resume_file:
        global resume_at
        resume_at = checkpoint
        resume_file.write(str(resume_at))
        logging.debug(f"Next time will resume from {resume_at}")

start_time = time.time()
try:
    with open(file_path, newline='') as csv_file, open(failures_path, 'w') as failures_csv:
        failures_writer = csv.DictWriter(failures_csv, fieldnames=['payload'])
        failures_writer.writeheader()

        reader = csv.DictReader(csv_file)
        count = 0
        success_count = 0
        unexpected_error_count = 0
        missing_prosecution_cases_count = 0
        already_exists_count = 0
        new_case_defendant_count = 0
        known_validation_errors = 0
        post_count = 0

        skip_to = 0
        stop_at = 1000
        try:
            with open(resume_file_path, 'r') as f:
                skip_to = int(f.readline())
                # stop_at = skip_to
                logging.info(f"Resuming from {skip_to}")
        except FileNotFoundError as e:
            logging.info(f"No resume.txt, starting from 0")
            pass

        for row in reader:
            count += 1
            if count < skip_to:
                logging.debug(f"Skipping {count}")
                resume_at = count
                continue
            else:
                if count > stop_at:
                    logging.debug(f"Stopping now")
                    break
                logging.debug(f"Processing entry {count}")

            row_dict = json.loads(row['payload'])
            try:
                hearing_id = row_dict['id']
                case_id = row_dict['prosecutionCases'][0]['id']
                court_code = row_dict.get('courtCentre', {}).get('code', "")[:-2]

                defendant_statuses = []
                locations = []
                for defendant in row_dict['prosecutionCases'][0]['defendants']:
                    get_url = GET_CASE_TEMPLATE % (case_id, defendant['id'])
                    r = requests.get(get_url, headers={'Authorization': f"Bearer {COURT_CASE_TOKEN}"})
                    # logging.debug(f"{r.status_code} from {get_url}")
                    defendant_statuses += [r.status_code]
                    if r.status_code == 404:
                        new_case_defendant_count += 1

                    if court_code:
                        locations.append(f"{PAC_HOST}/{court_code}/case/{case_id}/defendant/{defendant['id']}/summary")


                def is404(status):
                    return status == 404

                def is200(status):
                    return status == 200


                if all(map(is404, defendant_statuses)):
                    body = "{\"hearing\":%s}" % row['payload']
                    # logging.debug(body)
                    post_url = POST_HEARING_TEMPLATE % hearing_id
                    logging.debug(f"Posting {post_url}")
                    headers = {
                        'Authorization': f"Bearer {CHER_TOKEN}",
                        'Content-Type': "application/json"
                    }
                    r = requests.post(post_url, headers=headers, data=body.encode('utf-8'))
                    logging.debug(f"Received {r.status_code} from {post_url}")
                    post_count += 1
                    if r.status_code == 200:
                        logging.info(f"New case will be visible here: {', '.join(locations)}")
                    else:
                        if "parameter caseURN which is a non-nullable type" in r.text:
                            logging.debug(f"Case {case_id} contained no caseURN, skipping")
                            known_validation_errors += 1
                            checkpoint(count + 1)
                            continue
                        if "parameter code which is a non-nullable type" in r.text:
                            logging.debug(f"Case {case_id} contained no courtCode, skipping")
                            known_validation_errors += 1
                            checkpoint(count + 1)
                            continue
                        if "parameter roomId which is a non-nullable type" in r.text:
                            logging.debug(f"Case {case_id} contained no roomId, skipping")
                            known_validation_errors += 1
                            checkpoint(count + 1)
                            continue
                        raise Exception(r.status_code, r.text)

                else:
                    if all(map(is200, defendant_statuses)):
                        logging.debug(f"Case {case_id} already exists, skipping POST")
                        logging.info(f"Existing case will be visible here: {', '.join(locations)}")
                        already_exists_count += 1
                        checkpoint(count + 1)
                        continue
                    logging.error(f"Unexpected statuses: {defendant_statuses}.")
                    failures_writer.writerow(row)

                    checkpoint(count)
                    raise Exception(f"Aborting due to unexpected statuses from GET case/defendant {defendant_statuses}")

            except KeyError as e:
                if e.args[0] == 'prosecutionCases':
                    missing_prosecution_cases_count += 1
                    # logging.debug(f"No prosecution cases for hearingId {hearing_id}, skipping.")
                    checkpoint(count + 1)
                    continue
                unexpected_error_count += 1
                logging.error(f"Unexpected KeyError for hearingId: {hearing_id}")
                logging.error(e)
                checkpoint(count)
                failures_writer.writerow(row)
                # raise e
            except Exception as e:
                logging.debug(e)
                unexpected_error_count += 1
                checkpoint(count)
                failures_writer.writerow(row)
                # raise e

            checkpoint(count + 1)
            success_count += 1
finally:
    logging.info(f"Next time will resume from {resume_at}")
    logging.info(f"Successfully processed {success_count} cases. There were {already_exists_count} cases which already existed, {known_validation_errors} known validation errors, {unexpected_error_count} unexpected errors and {missing_prosecution_cases_count} hearings with no prosecutionCases", )
    logging.info(f"Attempted posts: {post_count}", )
    logging.info(f"Execution time was {time.time() - start_time} seconds")
