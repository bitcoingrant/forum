import flask, crypto, hashlib, string, binascii, generate_keypair
import traceback
from flask import render_template, request, abort
from pprint import pprint

app = flask.Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def home():
    """ Default route for cryptoapi web interface """
    print request.form.keys()
    result = {'username':'','password':'','public_key':'','message':''}
    
    if 'sendUserPass' in request.form.keys():
        try:
            priv_key = get_priv(str(request.form['username'])+str(request.form['password']))
            result = get_keypair(priv_key)
            #the following two lines here and at similarly in the next area are gross, something like a for loop should be done
            #to pass back defined values present during the post - thereby keeping permanence on the page
            result['username'] = request.form['username']
            result['password'] = request.form['password']
            print result
        except Exception as e:
            print 'Error: ' + str(e)
    elif 'sendPrivKey' in request.form.keys():
        try:
            priv_key = request.form['priv_key']
            result = get_keypair(priv_key)
            #the following two lines here and at similarly in the next area are gross, something like a for loop should be done
            #to pass back defined values present during the post - thereby keeping permanence on the page
            print result
        except Exception as e:
            print 'Error: ' + str(e)
    
    
    elif 'encryptMessage' in request.form.keys():
        try:
            result['public_key'] = request.form['public_key']
            result['message'] = request.form['message']
            somedict={'public_key':request.form['public_key'],'message':request.form['message']}
            result['encrypted_message'] = encrypt_message(somedict) 
            #this doesn't work yet because I have to figure out how to get the public key - I don't think I can get it just
            #from the bitcoin address unfortunately :(
        except Exception as e:
            print 'Error: ' + str(e)
            
    return render_template('index.html', result=result)

@app.route("/get_priv/<user_data>", methods=['POST'])
def get_priv(user_data):
    """ Create a deterministic private key from a username and password """
    return hashlib.sha256(user_data).hexdigest()

@app.route("/convert_to_wif", methods=['POST'])
def convert_to_wif():
    """ Convert hex-encoded private key to Wallet Import Format """
    #XXX: Untested
    #http://gobittest.appspot.com/PrivateKey and https://en.bitcoin.it/wiki/Wallet_import_format
    try:
        #step 1
        priv_key = request.form['priv_key'] 
        priv_key.lstrip("0x")
        if not all(c in string.hexdigits for c in priv_key):
            raise Exception("Not a valid private key input, must be hex")
        print "Step 1: " + priv_key
        #step 2
        priv_key = "80" + priv_key
        print "Step 2: " + priv_key
        #step 3
        priv_hash = hashlib.sha256(binascii.unhexlify(priv_key)).hexdigest()
        print "Step 3: " + priv_hash
        #step 4
        priv_hash = hashlib.sha256(binascii.unhexlify(priv_hash)).hexdigest()
        print "Step 4: " + priv_hash
        #step 5
        checksum = priv_hash[0:8]
        print "Checksum: " + checksum
        #step 6
        priv_key += checksum
        print "Step 6: " + priv_key
        #step 7
        priv_key = generate_keypair.b58encode(priv_key.decode("hex"))
        print "Step 7: " + priv_key
        
        return priv_key
    except Exception as e:
        print str(e)
        
#@app.route("/get_keypair/<priv_key>", methods=['POST'])
def get_keypair(priv_key):
    """Get a valid bitcoin keypair"""
    keypair = {'public_key':generate_keypair.generate_btc_address(int(priv_key,16))[3],'private_key':str(priv_key)}

    return keypair

@app.route("/get_btcaddress", methods=['POST'])
def get_btcaddress():
    """ Get Bitcoin address for public key """
    try:        
        return str(get_keypair(request.form['priv_key'])['public_key'])
    except Exception as e:
        print 'Error: ' + str(e)

#Encrypt a message with a bitcoin address
@app.route("/encrypt/<somedict>", methods=['POST'])
def encrypt_message(somedict):
    """
    Grab the pub key and message from the json, encrypt the message using the pub key,
    return the encrypted message
    """
    #XXX:WIP
    if somedict['message']: somedict['message'] = 'pretend this message is encypted now'
    return somedict

@app.route("/sign", methods=['POST'])
def sign_message():
    """ ECDSA sign provided message with provided public key """
    try:
        priv_key = int(request.form['priv_key'], 16)
        message = request.form['message']
    except:
        abort(400)

    return generate_keypair.sign_message(priv_key, message)

@app.route("/check_sig", methods=['POST'])
def check_signature():
    """ Check that provided signature of provided message matches provided bitcoin address """
    try:
        signature = request.form['signature']
        print signature
        message = request.form['message']
        btc_addr = request.form.get('btc_addr', None)
    except Exception as e:
        print traceback.format_exc()
        abort(400)
    try:
        print btc_addr, signature, message
        return generate_keypair.EC_KEY.verify_message(btc_addr, signature, message)
    except:
        print traceback.format_exc()
        abort(400)

if __name__ == "__main__":
    app.run(debug=True)
