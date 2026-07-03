#!/usr/bin/env python3
# check_proxmox_backup.py | (c) James Powell  2026
# inspired by https://forum.proxmox.com/threads/monitoring-proxmox-backup-server.77101/

import os, sys, requests, urllib3, argparse, time

urllib3.disable_warnings()
from collections import Counter

def read_token_from_file(path: str) -> str:
    """read API token from a file, stripping whitespace"""
    try:
        with open(path, "r") as f:
            token = f.read().strip()
        if not token:
            print(f"UNKNOWN: Token file '{path}' is empty")
            sys.exit(3)
        return token
    except OSError as e:
        print(f"UNKNOWN: Cannot read token file '{path}' ({e})")
        sys.exit(3)

def getargs() -> argparse.Namespace:
    """parse CL args"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--fqdn", help="fqdn of PMBS")
    parser.add_argument("-d", "--duration", help="seconds back to check",
                        type=int, default=86400)
    parser.add_argument("-v", "--verbose", action="store_true", help="more detail on jobs")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-t", "--token", help="API token: <username>@pbs!<api id>:<api secret>")
    group.add_argument("-c", "--config-token-file", help="path to file containing the API token", metavar="FILE")
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(3)
    args = parser.parse_args()
    if args.config_token_file:
        args.token = read_token_from_file(args.config_token_file)
    if not args.token:
        parser.error("one of -t/--token or -c/--config-token-file is required")
    return args

def query_pmbs(args, host="localhost", worker_type="backup") -> tuple[str, int|None, int|None, int|None, list]:
    """returns optional error string & # of ok, error, warning jobs & list of jobdetails"""
    error = ""
    starttime = int(time.time()) - args.duration
    jobcount = Counter({'OK': 0, 'ERROR': 0, 'WARNING': 0})
    url = f"https://{args.fqdn}:8007/api2/json/nodes/{host}/tasks?limit=0&since={starttime}"
    jobdetails = []
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
                if worker_type is not None and job.get("worker_type", "") != worker_type:
                    # skip non-specified tasks (eg aptupdate)
                    continue
                if os.getenv("CBPDEBUG"):
                    print(job, "\n")
                if args.verbose and job["status"] == "OK":
                    # build list of successful jobs by VM
                    jobdetails.append(job["worker_id"].split("/")[-1])
                jobcount.update({ job["status"] : 1 })
        else:
            error = f"Unexpected status code: {resp.status_code}"
    except requests.exceptions.RequestException as e:
        error = f"Failed to access https://{args.fqdn}:8007 ({e})"
    return error, jobcount["OK"], jobcount["ERROR"], jobcount["WARNING"], jobdetails

def output_quit(status, ok_taskcount, error_taskcount, warning_taskcount, exitcode, jobdetails):
    if exitcode == 3:
        status_info = ""
    else:
        status_info = f" success={ok_taskcount} errors={error_taskcount} warnings={warning_taskcount}"
        if jobdetails:
            status_info += " / Successful VMIDs: " + ",".join(jobdetails)
    print(
        f"SERVICE STATUS: {status}{status_info}"
    )
    sys.exit(exitcode)


def process_jobcounts(args, error, job_ok, job_error, job_warning, jobdetails):
    if not args.verbose:
        jobdetails = []
    if error:
        output_quit(f"UNKNOWN: {error}", job_ok, job_error, job_warning, 3, jobdetails)
    # OK If no errors and warning
    elif job_error == 0 and job_warning == 0:
        output_quit("OK", job_ok, job_error, job_warning, 0, jobdetails)
    # Warning if no errors and one or more warnings
    elif job_error == 0 and job_warning > 0:
        output_quit("WARNING", job_ok, job_error, job_warning, 1, jobdetails)
    # Error in case of one or more errors
    elif job_error > 0:
        output_quit("ERROR", job_ok, job_error, job_warning, 2, jobdetails)


def main():
    args = getargs()
    error, job_ok, job_error, job_warning, jobdetails = query_pmbs(args)
    process_jobcounts(args, error, job_ok, job_error, job_warning, jobdetails)

if __name__ == "__main__":
    main()
