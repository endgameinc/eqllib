.. include:: ../links.rst

==========================
Guide to Microsoft Sysmon
==========================
`Microsoft Sysmon`_ is a freely available tool provided by SysInternals for endpoint logging.


Installing Sysmon
-----------------
:download:`Download<https://download.sysinternals.com/files/Sysmon.zip>` Sysmon from SysInternals.

To install Sysmon, from a terminal, simply change to the directory where the unzipped binary is located, then run
the following command as an Administrator


To capture all default event types, with all hashing algorithms, run

.. code-block:: powershell

    Sysmon.exe -AcceptEula -i -h * -n -l

To configure Sysmon with a specific XML configuration file, run

.. code-block:: powershell

    Sysmon.exe -AcceptEula -i myconfig.xml

Full details of what each flag does can be found on the `Microsoft Sysmon`_ page

.. warning::
   Depending on the configuration, Sysmon can generate a significant amount of data.
   When deploying Sysmon to production or enterprise environments, it is usually best to tune it to your specific environment.
   There are several Sysmon configuration files in common use which can be used or referenced for this purpose.

   - @SwiftOnSecurity's `scalable config file <https://github.com/SwiftOnSecurity/Sysmon-config#readme>`_.
   - @olafhartong's more `verbose config file <https://github.com/olafhartong/Sysmon-modular#readme>`_.


Getting Sysmon logs with PowerShell
-----------------------------------
Helpful PowerShell functions for parsing Sysmon events from Windows Event Logs are found in the Github at `utils/scrape-events.ps1 <https://github.com/endgameinc/eqllib/tree/master/utils/scrape-events.ps1>`_

Getting logs into JSON format can be done by piping to PowerShell cmdlets within an elevated ``powershell.exe`` console.

.. code-block:: powershell

    # Import the functions provided within scrape-events
    Import-Module .\utils\scrape-events.ps1

    # Save the most recent 5000 Sysmon logs
    Get-LatestLogs  | ConvertTo-Json | Out-File -Encoding ASCII -FilePath my-sysmon-data.json

    # Save the most recent 1000 Sysmon process creation events
    Get-LatestProcesses | ConvertTo-Json | Out-File -Encoding ASCII -FilePath my-sysmon-data.json


To get *all* Sysmon logs from Windows Event Logs, run the powershell command

.. code-block:: powershell

    Get-WinEvent -filterhashtable @{logname="Microsoft-Windows-Sysmon/Operational"} | Get-EventProps | ConvertTo-Json | Out-File -Encoding ASCII -FilePath my-sysmon-data.json

.. warning::
    Use this with caution as it will process all events, which may take time and likely generate a large file


Example searches with EQL
-------------------------

Once you have logs in JSON format, they can now be queried using EQL. To do so, either the *query* or the *data* will
need to be converted (normalized). Because EQL is built to be able to be flexible across all data sources, it
is necessary to translate the query to match the underlying data, or to change the data to match the query.
The conversion functionality is described in more detail in the :doc:`cli` guide.


For example, to find suspicious reconnaissance commands over the generated data

.. code-block:: powershell

    eqllib query -f my-sysmon-data.json --source "Microsoft Sysmon" "process where process_name in ('ipconfig.exe', 'netstat.exe', 'systeminfo.exe', 'route.exe')"

