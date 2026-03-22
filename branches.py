# --- Configuration ---
# The name of your remote for the upstream repository.
# Note: If running this in GitHub Actions, you must manually add the upstream remote first, e.g.:
#       git remote add upstream https://github.com/micropython/micropython.git
#
# micropython/micropython repository integration branches configuration.
UPSTREAM_REMOTE = "upstream"
MAIN_BRANCH = "master"

# foo/micropython
ORIGIN_REMOTE = "origin"
# The primary branch on your fork that tracks the upstream repository.
DEFAULT_TARGET = "master_jv"


BASE = [
        "jv/devcontainer",
        "jv/my_membrowse",
        "jv/mpremote_publish",
        ]

integration_branches = {
    "master_jv": {
        "target_branch": "master_jv",
        "sources": BASE
    },
    "mpremote": {
        "target_branch": "integration/mpremote",
        "sources": BASE + [
                # # 8231, # tools/mpremote: Add manifest function. 
                # # 11764, # tools/mpremote/mpremote/mip: Allow target dir in package deps
                # # 14141, # tools/mpremote: Add ws:// and wss:// endpoints. (OLD - REBASE NEEDED )
                # 14374, # mpremote: do not list bogus devices
                17322, # tools/mpremote: Add automatic reconnection feature
                # # 17646, # tools/mpremote: Add metadata file and new subcommands for mip
                # 18298, # Add tell support for mounted files
                # 18436, # tools/mpremote: Add streaming hash verification to file transfers
                # # 18712, # tools/mpremote: Add mip download and mpy version handling.

                (18785,"-Xtheirs"), # mpremote: Speed up file transfers with automatic encoding
                ("PR/mpr/unicode", "-Xtheirs"), # Fix multiple unicode issues in mpremote
                ("patch/mpremote_transport__quote_path", "-Xtheirs"), # Fix quoting of paths with spaces in mpremote transport

        ]
    },
    "CI": {
        "target_branch": "integration/CI",
        "sources": BASE + [
                "PR/pr_status_action",
        ]
    },
    "docs": {
        "target_branch": "integration/docs",
        "sources": BASE + [

                # 8072, #docs\machine: Add Counter and Encoder classes.
                14163, # docs/library: Add docs for ntptime.py module.

                15320, # Update os.rst - addendum to sync
                15587, # docs/framebuf: Add minimal buffer size requirements.

                16842, # docs/library/enum.rst: Add Enum class. 
                17038, #Document that a Pin can be passed to UART constructor on the ESP32 ports. 
                17263, # docs: Add documentation for the io.IOBase class. 
                17301, #  Improve documentation for writing and running tests 
                17456, # unix: Extend README with fully static builds section.
                17788, # Docs: Add build requirements for macOS M-Series Macs. 
                17806, # docs/porting: Update session log. 
                17826, # docs/esp32: Use new esptool syntax. 
                18133, # rp2: Add execctrl option for the PIO decorator. 
                18606, # fix machine.Encoder example (use Encoder instead of Counter) 
                18697, # Update general and PIO docs for RP2350 support. 
                18714, # Improve micropython.const() documentation and consistency 
                18744,
                18978, #  Document Pin.board and Pin.cpu attributes.
        ]
    },
    "unicode": {
        "target_branch": "integration/unicode",
        "sources": BASE + [
                "PR/mpr/unicode",
                "core/unicode",
        ]
    }
}

