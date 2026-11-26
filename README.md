# check_proxmox_backup

An Icinga/Nagios compatible plugin to check the status of **Proxmox Backup Server (PBS)** backup jobs.

This script queries the Proxmox Backup Server API to retrieve task statuses (specifically `backup` worker types) over a specified duration (default: last 24 hours) and reports the counts of success, warning, and error jobs.

## Features

- Checks backup job statuses for the last 24 hours (configurable).
- Standard Nagios/Icinga exit codes (0=OK, 1=WARNING, 2=CRITICAL, 3=UNKNOWN).
- Reports counts of successful, warning, and error jobs.
- Secure API Token authentication (inline or from file).
- Optional verbose output listing successful VMIDs.

## Requirements

- Python 3
- `requests` library

Install dependencies manually:

```bash
pip3 install requests
```

Or using the provided `requirements.txt`:

```bash
pip3 install -r requirements.txt
```

Or just through your system package manager.

## Setup

### 1. Create an API Token on Proxmox Backup Server

1. Log in to your Proxmox Backup Server web interface.
2. Go to **Configuration** -> **Access Control**.
3. Select the **API Token** tab and click **Add**.
4. Select a user (e.g., `root@pam` or (better) a dedicated monitoring user) and enter a Token ID (e.g., `nagios`).
5. **Important:** Uncheck "Privilege Separation" if you want the token to inherit the user's permissions, or configure specific permissions for the token afterwards.
6. Copy the **Secret** value immediately. You will need it for the script argument.

The full token format usually looks like: `user@realm!tokenid:secretvalue`
Example: `root@pam!nagios:8c005f00-1234-5678-90ab-cdef12345678`

### 2. Install the Script

Copy `check_proxmox_backup.py` to your Nagios/Icinga plugin directory (e.g., `/usr/lib/nagios/plugins/`).

```bash
chmod +x check_proxmox_backup.py
```

## Usage

```bash
./check_proxmox_backup.py -f <FQDN> { -t <TOKEN> | -c <TOKEN_FILE> } [-d <DURATION_SECONDS>] [-v]
```

### Arguments

- `-f`, `--fqdn`: The Fully Qualified Domain Name (or IP) of the Proxmox Backup Server.
- `-t`, `--token`: The API Token constructed as `<user>@<realm>!<tokenid>:<secret>`.
- `-c`, `--config-token-file`: Path to a file containing the API token (alternative to `-t`; useful for keeping secrets out of process lists and command history).
- `-d`, `--duration`: (Optional) Time in seconds to look back for jobs. Default is `86400` (24 hours).
- `-v`, `--verbose`: (Optional) Include a list of successful VMIDs in the output.

> **Note:** `-t` and `-c` are mutually exclusive; exactly one must be provided.

## Examples

**Manual Check (token inline):**

```bash
./check_proxmox_backup.py -f pbs.example.com -t "root@pam!monitoring:secret-key-here"
```

**Manual Check (token from file):**

```bash
./check_proxmox_backup.py -f pbs.example.com -c /etc/nagios/pbs_token.txt
```

**Verbose output:**

```bash
./check_proxmox_backup.py -f pbs.example.com -c /etc/nagios/pbs_token.txt -v
```

**Output:**
```text
SERVICE STATUS: OK success=15 errors=0 warnings=0
SERVICE STATUS: OK success=15 errors=0 warnings=0 / Successful VMIDs: 101,102,103
```

**Icinga 2 Service definition example:**

```conf
object CheckCommand "check_pbs" {
  import "plugin-check-command"
  command = [ PluginDir + "/check_proxmox_backup.py" ]
  arguments = {
    "-f" = "$pbs_fqdn$"
    "-t" = {
      value = "$pbs_token$"
      required = false
    }
    "-c" = {
      value = "$pbs_token_file$"
      required = false
    }
    "-d" = {
      value = "$pbs_duration$"
      required = false
    }
    "-v" = {
      set_if = "$pbs_verbose$"
    }
  }
}

object Service "pbs_backups" {
  import "generic-service"
  host_name = "pbs-server"
  check_command = "check_pbs"
  vars.pbs_fqdn = "pbs.example.com"
  vars.pbs_token = "root@pam!monitoring:secret-key-here"
}
```

## License

(c) James Powell 2026
