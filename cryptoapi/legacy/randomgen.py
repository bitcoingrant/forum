import os
from subprocess import Popen, PIPE


keysAreValid = False

while keysAreValid == False:

    process = Popen(["./vanitygen", "-s","/dev/random", "-q", "-t"," 1", "1"], stdout=PIPE)

    print "process: " + str(process)

    results = process.stdout.read()
    
    print "results: " + str(results)
    
    addrs = results.split()
    
    print "addrs: " + str(addrs)
    
    pubkey = addrs[3]
    privkey = addrs[5]

#we do a basic length sanity check on the public and private keys
    if len(privkey) == 51 and len(pubkey) == 34:
        keysAreValid = True
    else:
        keysAreValid = False 