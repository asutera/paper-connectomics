DATA_DIRECTORY = ~/scikit_learn_data/connectomics
GIT_DIRECTORY = ~/git/paper-connectomics
HOST = hercules

launch: sync-git
	ssh ${HOST} "cd ${GIT_DIRECTORY}/crowdsource/code && python launcher.py"

launch-debug: sync-git
	ssh ${HOST} "cd ${GIT_DIRECTORY}/crowdsource/code && python launcher.py -dv"

launch-result: sync-git
	ssh ${HOST} "cd ${GIT_DIRECTORY}/crowdsource/code && python launcher.py -ds"

retrieve:
	rsync -avz -e ssh ${HOST}:${DATA_DIRECTORY}/*.sqlite3 ${DATA_DIRECTORY}
	rsync -avz -e ssh ${HOST}:${DATA_DIRECTORY}/submission ${DATA_DIRECTORY}
	rsync -avz -e ssh ${HOST}:${DATA_DIRECTORY}/*.xls ${DATA_DIRECTORY}

summary:
	python launch.py -sd

# -----------------------------------------------------------------------------
logs:
	ssh ${HOST} 'cd ${DATA_DIRECTORY}/logs && \
			  for file in `ls`; \
				  do echo "==================="; \
				  echo $$file; \
				  cat $$file; \
			  done'

# Synchronisation
sync-git:
	git push
	ssh -A ${HOST} "cd ${GIT_DIRECTORY} && git pull"

sync-clean: sync-git sync-clean-cache
	ssh ${HOST} "cd ${GIT_DIRECTORY} && make clean-logs"

sync-clean-cache: sync-git
	ssh ${HOST} "cd ${GIT_DIRECTORY} && make clean-cache"

# Cleaner helper
clean:
	rm *.pyc

clean-cache:
	rm -rf ${DATA_DIRECTORY}/cache_dir

clean-logs:
	cd ${DATA_DIRECTORY}/logs && rm *
	mkdir -p ${DATA_DIRECTORY}/logs



# retrieve-performance:
# 	scp ${HOST}:${DATA_DIRECTORY}/exploration_performance.sqlite3 ${DATA_DIRECTORY}


# -----------------------------------------------------------------------------
# Unix command helper
top:
	ssh ${HOST} -tt top

htop:
	ssh ${HOST} -tt htop

squeue:
	ssh ${HOST} 'squeue -u ajoly -a -o "%.7i %.9P %40j %.8T %.4C %.10m %.10M %.10l %R" '

scancel-all:
	ssh ${HOST} "scancel -u ajoly"

sacct:
	ssh ${HOST} 'sacct -u ajoly --format JobID,JobName,AveCPU,cputime,elapsed,MaxVMSize,MaxVMSizeNode,MaxRSS'

smem:
	ssh ${HOST} 'for node in `squeue -u ajoly -o "%N" -h | uniq | sort`; \
					do echo "$$node===="; \
					ssh $$node "top -b -n 1 -i -u ajoly" ; \
				 done'

which-python:
	ssh ${HOST} "which python"

echo-shell:
	ssh ${HOST} "echo $${SHELL}"

echo-path:
	ssh ${HOST} "source .zshrc && echo $${PATH}"
