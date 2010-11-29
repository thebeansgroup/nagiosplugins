<?php
/*
 * Cron-invoked monitoring script. This retrieves data from mysql, memcached
 * and apache and pushes statistics into gmetric.
 */
class Monitor
{
	// path to the gmetric binary
	var $gmetric = '/usr/bin/gmetric';
	
	// path to a file used to save metrics between invocations
	var $metricStore = '/usr/local/bin/metricStore';
	
	// array to save data from the previous invocation in
	var $oldData = array();
	
	// an array to save data from this round of gathering
	var $metrics = array();
	
	// an array to save data from that hasn't been divided by delta uptime
	var $straightMetrics = array();
	
	/*
	 * an array of data to collect.
	 * 'command' will be executed to retrieve data.
	 * keys in the 'metrics' array are keys in the data returned by executing 
	 * 'command'. each key will be searched for in the output of 'command', and the
	 * number given after it will be taken as that data's value.
	 *
	 * After populating a data array, a function will be called (if it exists) called
	 * 'processMemcached'/'processApache', etc. This can calculate ratios, or normalise
	 * data, etc before sending it to gmetric. If an entry has 'nodelta' == true, the raw
	 * value will be submitted, not the delta between invocations.
	 *
	 * This array also contains a field called 'uptime_key' which is the array key to use 
	 * to find the uptime for the service. We'll divide all values that we do find the 
	 * delta for by the delta of the uptime, to give a value per second for that data.
	 */
	var $metricDefinitions = array
	(
		'Memcached' => array
		(
			'command' => 'echo -ne "stats\r\n" | nc -i1 localhost 11211',
			'uptime_key' => 'uptime',
			'metrics' => array
			(
				'uptime' => array('name' => 'mcd_uptime', 'type' => 'uint32', 'units' => 'seconds', 'nodelta' => true),
				'curr_items' => array('name' => 'mcd_curr_items', 'type' => 'float', 'units' => 'items', 'nodelta' => true),
				'total_items' => array('name' => 'mcd_total_items', 'type' => 'uint32', 'units' => 'items', 'nodelta' => true),
				'bytes' => array('name' => 'mcd_bytes_used', 'type' => 'uint32', 'units' => 'bytes', 'nodelta' => true),
				//'limit_maxbytes' => array('name' => 'mcd_mem_limit', 'type' => 'uint32', 'units' => 'kilobytes', 'nodelta' => true),
				'total_connections' => array('name' => 'mcd_total_conns', 'type' => 'float', 'units' => 'connections/secs'),
				// we'll divide this by delatTime ourselves after computing a hit percentage
				'cmd_get' => array('name' => 'mcd_gets', 'type' => 'float', 'units' => 'gets/secs', 'nodelta' => true),
				// same here
				'get_hits' => array('name' => 'mcd_cache_hits', 'type' => 'float', 'units' => 'cache hits/secs', 'nodelta' => true),
				'cmd_set' => array('name' => 'mcd_sets', 'type' => 'float', 'units' => 'sets/secs'),
				'get_misses' => array('name' => 'mcd_cache_misses', 'type' => 'float', 'units' => 'cache misses/secs'),
				'evictions' => array('name' => 'mcd_evictions', 'type' => 'float', 'units' => 'evictions/secs'),
				'bytes_written' => array('name' => 'mcd_bytes_written', 'type' => 'float', 'units' => 'bytes/secs')
			)
		),/*
		'Mysql' => array
		(
			'command' => "mysql -e 'show status;'",
			'uptime_key' => 'Uptime',
			'metrics' => array
			(
				'Uptime' => array('name' => 'db_uptime', 'type' => 'uint32', 'units' => 'seconds', 'nodelta' => true),
				'Com_delete' => array('name' => 'db_deletes', 'type' => 'float', 'units' => 'deletes/secs'),
				'Com_insert' => array('name' => 'db_inserts', 'type' => 'float', 'units' => 'inserts/secs'),
				'Com_replace' => array('name' => 'db_replaces', 'type' => 'float', 'units' => 'replaces/secs'),
				'Com_select' => array('name' => 'db_selects', 'type' => 'float', 'units' => 'selects/secs'),
				'Com_update' => array('name' => 'db_updates', 'type' => 'float', 'units' => 'updates/secs'),
				'Connections' => array('name' => 'db_total_conn_attempts', 'type' => 'float', 'units' => 'connection attempts/secs'),
				'Max_used_connections' => array('name' => 'db_max_sim_conns', 'type' => 'uint32', 'units' => 'simultaneous connections', 'nodelta' => true),
				'Qcache_free_memory' => array('name' => 'db_qcache_free_mem', 'type' => 'uint32', 'units' => 'bytes', 'nodelta' => true),
				'Qcache_lowmem_prunes' => array('name' => 'db_qcache_lowmem_prunes', 'type' => 'float', 'units' => 'prunes/secs'),
				'Questions' => array('name' => 'db_total_questions', 'type' => 'float', 'units' => 'questions/secs'),
				'Select_full_join' => array('name' => 'db_select_full_join', 'type' => 'float', 'units' => 'full join selects/secs'),
				'Table_locks_immediate' => array('name' => 'db_table_locks_immediate', 'type' => 'float', 'units' => 'table locks/secs'),
				'Table_locks_waited' => array('name' => 'db_table_locks_waited', 'type' => 'float', 'units' => 'table locks/secs'),
				'Threads_cached' => array('name' => 'db_threads_cached', 'type' => 'uint32', 'units' => 'threads', 'nodelta' => true),
				'Threads_connected' => array('name' => 'db_threads_connected', 'type' => 'uint32', 'units' => 'threads', 'nodelta' => true),
				'Threads_created' => array('name' => 'db_threads_created', 'type' => 'uint32', 'units' => 'threads', 'nodelta' => true),
				'Threads_running' => array('name' => 'db_threads_running', 'type' => 'uint32', 'units' => 'threads', 'nodelta' => true),
			)
		),*/
		'Apache' => array
		(
			'command' => "wget -q -O - http://localhost/server-status/?auto",
			'uptime_key' => 'Uptime',
			'metrics' => array
			(
				'Uptime' => array('name' => 'apache_uptime', 'type' => 'uint32', 'units' => 'seconds', 'nodelta' => true),
				'Total Accesses' => array('name' => 'apache_total_accesses', 'type' => 'float', 'units' => 'accesses/secs'),
				'Total kBytes' => array('name' => 'apache_total_kbytes', 'type' => 'float', 'units' => 'kbytes', 'nodelta' => true),
				'CPULoad' => array('name' => 'apache_cpu_load', 'type' => 'float', 'units' => 'cpu load', 'nodelta' => true),
				'ReqPerSec' => array('name' => 'apache_requests_per_second', 'type' => 'float', 'units' => 'requests/sec', 'nodelta' => true),
				'BytesPerSec' => array('name' => 'apache_bytes_per_second', 'type' => 'float', 'units' => 'bytes/sec', 'nodelta' => true),
				'BusyWorkers' => array('name' => 'apache_busy_workers', 'type' => 'uint32', 'units' => 'workers', 'nodelta' => true),
				'IdleWorkers' => array('name' => 'apache_idle_workers', 'type' => 'uint32', 'units' => 'workers', 'nodelta' => true),
			)
		)
	);
	
	/**
	 * Controls the whole metric-gathering process.
	 */
	public function getMetrics()
	{
		echo "Gathering custom metrics...\n";
		
		foreach($this->metricDefinitions as $k => $v)
		{
			echo "Getting metrics for ".strtolower($k)."...\n";
			
			$this->metrics = $this->getMetricData($k, $v);
						
			// call custom function if it exists
			if (method_exists($this, 'process'.$k))
			{
				$function = 'process'.$k;
				$this->$function();
			}
		}
		
		echo "Submitting metrics...\n";
		$this->submitData();
			
		echo "Metrics gathered.\n";
	}
	
	/**
	 * Works through the array defined above, populating a data array which it returns.
	 * @param string $key The key for the metrics we're getting.
	 * @param array &$array Our array that defines what to gather.
	 * @return array Array of metrics data.
	 */
	private function getMetricData($key, &$array)
	{
		// get data from the last run if it's set
		$this->oldData = (count($this->oldData) == 0) ? $this->getLastMetrics() : $this->oldData;
		
		$rawData = shell_exec($array['command']);

		// work through the metrics array, saving metrics from $rawData after subtracting
		// from $oldData
		
		// array to save matches into
		$value = array();
		
		foreach ($array['metrics'] as $k => $v)
		{
			preg_match("/$k\b.*\s([0-9\.]+)/", $rawData, $value);
			
			// in case of a server/service restart, we need to make sure the delta is >= 0
			$newValue = (!isset($v['nodelta']) && ($value[1] - $this->oldData[$key]['metrics'][$k]['value']) >= 0) ? $value[1] - $this->oldData[$key]['metrics'][$k]['value'] : $value[1];
			
			if (!isset($v['nodelta']))
			{
				// get the time since the service was last polled.
				if (!isset($uptimeDelta) && $this->metrics[$key]['metrics'][$array['uptime_key']]['value']-$this->oldData[$key]['metrics'][$array['uptime_key']]['value'] >= 0)
				{
					$uptimeDelta = $this->metrics[$key]['metrics'][$array['uptime_key']]['value']-$this->oldData[$key]['metrics'][$array['uptime_key']]['value'];
				}
				else if (isset($uptimeDelta))
				{
					$uptimeDelta = $uptimeDelta;
				}
				else		// if this is the first run, and no value is in the oldData array, or the service
							// has been restarted, just get the value
				{
					$uptimeDelta = $this->metrics[$key]['metrics'][$array['uptime_key']]['value'];
				}
					
				$this->metrics[$key]['metrics'][$k] = array('value' => round($newValue/$uptimeDelta, 2), 'name' => $v['name'], 'type' => $v['type'], 'units' => $v['units']);
				
				if (!isset($uptimeShown))
				{
					echo "$key service last polled $uptimeDelta seconds ago.\n";
					$uptimeShown = true;
				}
			}
			else
			{
				$this->metrics[$key]['metrics'][$k] = array('value' => $newValue, 'name' => $v['name'], 'type' => $v['type'], 'units' => $v['units']);
			}
			
			// save the raw, non-deltad metric
			$this->straightMetrics[$key]['metrics'][$k] = array('value' => $value[1], 'name' => $v['name'], 'type' => $v['type'], 'units' => $v['units']);
		}
		
		$this->metrics[$key]['uptimeDelta'] = $uptimeDelta;
		
		return $this->metrics;
	}
	
	/**
	 * Retrieves the last set of metrics from a file
	 * @return array An array of metric data from the previous invocation.
	 */
	private function getLastMetrics()
	{
		if ($file = fopen($this->metricStore, 'r'))
		{
			$this->oldData = unserialize(fread($file, filesize($this->metricStore)));
			fclose($file);
		}
		
		return $this->oldData;
	}
	
	/**
	 * Submits data to gmetric.
	 */
	private function submitData()
	{
		foreach ($this->metrics as $key => $valueArray)
		{
			foreach ($valueArray['metrics'] as $k => $v)
			{
				$command = "{$this->gmetric} --type={$v['type']} --name=\"{$v['name']}\" --value=\"{$v['value']}\" --units=\"{$v['units']}\"";
				system($command);
			}
		}
		
		// now save the straight metrics to a file for next time
		if ($file = fopen($this->metricStore, 'w+'))
		{
			fwrite($file, serialize($this->straightMetrics));
			fclose($file);
		}
	}
	
	/**
	 * Performs custom manipulation for the memcache stats.
	 */
	private function processMemcached()
	{
		$deltaGets = ($this->metrics['Memcached']['metrics']['cmd_get']['value']-$this->oldData['Memcached']['metrics']['cmd_get']['value'] >= 0) ? $this->metrics['Memcached']['metrics']['cmd_get']['value']-$this->oldData['Memcached']['metrics']['cmd_get']['value'] : $this->metrics['Memcached']['metrics']['cmd_get']['value'];
		$deltaCacheHits = ($this->metrics['Memcached']['metrics']['get_hits']['value']-$this->oldData['Memcached']['metrics']['get_hits']['value'] >= 0) ? $this->metrics['Memcached']['metrics']['get_hits']['value']-$this->oldData['Memcached']['metrics']['get_hits']['value'] : $this->metrics['Memcached']['metrics']['get_hits']['value'];
		
		$uptimeDelta = $this->metrics['Memcached']['uptimeDelta'];
		
		// save the cache hit percentage
		$this->metrics['Memcached']['metrics']['hits_percentage'] = array
		(
			'value' => round($deltaCacheHits * 100 / $deltaGets, 2),
			'units' => '%',
			'type' => 'float',
			'name' => 'mcd_cache_hits_percentage'
		);
		
		$this->metrics['Memcached']['metrics']['cmd_get']['value'] = round($deltaGets/$uptimeDelta, 2);
		$this->metrics['Memcached']['metrics']['get_hits']['value'] = round($deltaCacheHits/$uptimeDelta, 2);
		
		/*
		// no deltas are being created for this statistic, so no need to 
		// save it for next time
		$this->straightMetrics['Memcached']['metrics']['hits_percentage'] = array
		(
			'value' => round($cacheHits * 100 / $gets, 2),
			'units' => '%',
			'type' => 'float',
			'name' => 'mcd_cache_hits_percentage'
		);
		*/		
		
		/*
		foreach ($this->metrics as $key => $valuesArray)
		{
			foreach ($valuesArray as $k => $v)
			{
				switch ($k)
				{
				
				}
			}			
		}
		*/
	}
	
	/**
	 * Performs custom manipulation for the mysql stats.
	 */
	private function processMysql()
	{
	}
	
	/**
	 * Performs custom manipulation for the apache stats.
	 */
	private function processApache()
	{
	}
}

$monitor = new Monitor();
$monitor->getMetrics();

?>
