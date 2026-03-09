



integration_branches = {
    "master_jv": {
        "target_branch": "master_jv",
        "sources": [
                "jv/devcontainer",
                "jv/my_membrowse",
        ]
    },
    "mpremote": {
        "target_branch": "integration/mpremote",
        "sources": [
                # # 8231, # tools/mpremote: Add manifest function. 
                # # 11764, # tools/mpremote/mpremote/mip: Allow target dir in package deps
                # # 14141, # tools/mpremote: Add ws:// and wss:// endpoints. (OLD - REBASE NEEDED )
                14374, # mpremote: do not list bogus devices
                17322, # tools/mpremote: Add automatic reconnection feature
                # # 17646, # tools/mpremote: Add metadata file and new subcommands for mip
                # 18298, # Add tell support for mounted files
                # 18436, # tools/mpremote: Add streaming hash verification to file transfers
                # # 18712, # tools/mpremote: Add mip download and mpy version handling.
                # # 18785, # mpremote: Speed up file transfers with automatic encoding
                # # (18853, "-Xtheirs"), # Fix multiple unicode issues in mpremote
                # # ("patch/mpremote_transport__quote_path", "-Xtheirs"), # Fix quoting of paths with spaces in mpremote transport
                "jv/my_membrowse",
                "PR/pr_status_action",
        ]
    },
    "CI": {
        "target_branch": "integration/CI",
        "sources": [
                "jv/devcontainer",
                "jv/my_membrowse",
                "PR/pr_status_action",
        ]
    }
}

