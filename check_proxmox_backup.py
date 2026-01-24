#!/usr/bin/env python3
# check_proxmox_backup.py | (c) James Powell  2026
# inspired by https://forum.proxmox.com/threads/monitoring-proxmox-backup-server.77101/

import sys, requests, urllib3, argparse, time

urllib3.disable_warnings()
from collections import Counter

def getargs() -> argparse.Namespace:
    """parse CL args"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--fqdn", help="fqdn of PMBS")
    parser.add_argument("-t", "--token", help="API token: <username>@pbs!<api id>:<api secret>")
    parser.add_argument("-d", "--duration", help="seconds back to check",
                        type=int, default=86400)
    return parser.parse_args()

def query_pmbs(args, host="localhost", worker_type="backup") -> tuple[str, int|None, int|None, int|None]:
    """returns optional error string & # of ok, error, warning jobs"""
    error = ""
    starttime = int(time.time()) - args.duration
    jobcount = Counter({'OK': 0, 'ERROR': 0, 'WARNING': 0})
    url = f"https://{args.fqdn}:8007/api2/json/nodes/{host}/tasks?limit=0&since={starttime}"
    try:
        resp = requests.get(url,
            verify=False,
            timeout=5,
            headers={"Authorization": f"PBSAPIToken={args.token}"}
        )
        if resp.status_code == 401:
            error = f"Authentication failed for https://{args.fqdn}:8007"
        elif resp.status_code == 200:
            jsondata = resp.json()
            for job in jsondata["data"]:
                # print(jsondata["data"])  # DEBUG
                if worker_type is not None and job.get("worker_type", "") != worker_type:
                    # skip non-specified tasks (eg aptupdate)
                    continue
                jobcount.update({ job["status"] : 1 })
        else:
            error = f"Unexpected status code: {resp.status_code}"
    except requests.exceptions.RequestException as e:
        error = f"Failed to access https://{args.fqdn}:8007 ({e})"
    return error, jobcount["OK"], jobcount["ERROR"], jobcount["WARNING"]

def output_quit(status, ok_taskcount, error_taskcount, warning_taskcount, exitcode):
    if exitcode == 3:
        status_info = ""
    else:
        status_info = f" | success={ok_taskcount} errors={error_taskcount} warnings={warning_taskcount}"
    print(
        f"SERVICE STATUS: {status}{status_info}"
    )
    sys.exit(exitcode)


def process_jobcounts(error, job_ok, job_error, job_warning):
    if error:
        output_quit(f"UNKNOWN: {error}", job_ok, job_error, job_warning, 3)
    # OK If no errors and warning
    elif job_error == 0 and job_warning == 0:
        output_quit("OK", job_ok, job_error, job_warning, 0)
    # Warning if no errors and one or more warnings
    elif job_error == 0 and job_warning > 0:
        output_quit("WARNING", job_ok, job_error, job_warning, 1)
    # Error in case of one or more errors
    elif job_error > 0:
        output_quit("ERROR", job_ok, job_error, job_warning, 2)


def main():
    args = getargs()
    error, job_ok, job_error, job_warning = query_pmbs(args)
    process_jobcounts(error, job_ok, job_error, job_warning)

if __name__ == "__main__":
    main()