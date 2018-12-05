function Get-EventProps {
  [cmdletbinding()]
  Param (
    [parameter(ValueFromPipeline)]
    $event
  )
    Process {
        $eventXml = [xml]$event.ToXML()
        $eventKeys = $eventXml.Event.EventData.Data
        $Properties = @{}
        $Properties.EventId = $event.Id

        For ($i=0; $i -lt $eventKeys.Count; $i++) {
            $Properties[$eventKeys[$i].Name] = $eventKeys[$i].'#text'
        }

        [pscustomobject]$Properties
    }
}

function reverse {
 $arr = @($input)
 [array]::reverse($arr)
 $arr
}

function Get-LatestLogs {
    Get-WinEvent -filterhashtable @{logname="Microsoft-Windows-Sysmon/Operational"} -MaxEvents 5000 | Get-EventProps | reverse
}

function Get-LatestProcesses {
    Get-WinEvent -filterhashtable @{logname="Microsoft-Windows-Sysmon/Operational";id=1} -MaxEvents 1000 | Get-EventProps | reverse
}

