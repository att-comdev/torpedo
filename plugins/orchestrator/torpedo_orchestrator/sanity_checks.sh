LOG_DIR="/var/log/resiliency/$1_"`date +"%Y_%m_%d_%H_%M_%S"`
if [ ! -d $LOG_DIR ]
then
    mkdir -p $LOG_DIR
fi

end=$((SECONDS+$2))

while [ $SECONDS -lt $end ]
do
    timestamp=`date +"%Y_%m_%d_%H_%M_%S"`
    ceph_sanity_checks="$LOG_DIR/sanity_check_$timestamp.log"
    eval $3 2> $ceph_sanity_checks 
    sleep 120
done

