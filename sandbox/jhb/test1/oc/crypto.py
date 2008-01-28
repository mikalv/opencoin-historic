

#The following is for s60 compatibility 
import rsa

class SimpleKeyPair:
    def __init__(self,pub=None,priv=None,size=1024):
        if not pub and not priv:
            (pub,priv) =  rsa.gen_pubpriv_keys(size)
        self.privateKey = SimplePublicKey(priv)
        self.publicKey = SimplePrivateKey(pub)


class SimplePublicKey:
    
    def __init__(self,key):
        self.key = key

    def encrypt(self,message):
        return rsa.encrypt(message,self.key)

    def decrypt(self,message):
        return rsa.verify(message,self.key)


class SimplePrivateKey:
    
    def __init__(self,key):
        self.key = key

    def encrypt(self,message):
        return rsa.sign(message,self.key)

    def decrypt(self,message):
        return rsa.decrypt(message,self.key)




class MixedKeyPair:

    def __init__(self,pub=None,priv=None,size=1024):
        if not pub and not priv:
            import crypto_mathew as cm
            keypair =   cm.createRSAKeyPair(size)
            key = keypair.key
            priv = {'d': key.d, 'p': key.p, 'q': key.n}
            pub = {'e': key.e, 'n': key.n}

        self.privateKey = SimplePublicKey(pub)
        self.publicKey = SimplePrivateKey(priv)

#and now some faster key

class FastKeyPair:
    def __init__(self,pub=None,priv=None,size=1024):
        if not pub and not priv:
            print 'generating'
            keypair =  cm.createRSAKeyPair(size)
            private = keypair.private()
            public = keypair.public()
        self.privateKey = FastKey(private)
        self.publicKey = FastKey(public)

class FastKey:

    def __init__(self,key):
        self.key = key

    def encrypt(self,message):
        return self.key.encrypt(message,'')

    def decrypt(self,message):
        return self.key.decrypt(message)

    def sign(self,message):
        return self.key.sign(message,'')

    def verify(self,message):
        return self.key.verify(message)
     
print __name__     
if __name__ == '__main__':
    pub = {'e': 113958493785022709325122760262108637329447125102630296941836299402619973466291L, 'n': 20061324867686702850786705531870659181857526348052163958802936662597197228176654367220269165501439239594208262691509637109079673519079673165087263326124203930566599999597466733728460554273900738691949483728859397313671067510351730603988459558434974352588861838193053971773080798098585217998467161243657478107L} 
    priv = {'q': 2328974059054660854406421051713883494936740356397236849373731728612874003396794029713337251182953063481675691331928223848603530621694734304535726464864717L, 'p': 8613803485569808569764087718835703227060236097512644448795705652962933785914160674747662526209592633104697018013684263986826565034130772820767411392409671L, 'd': 4259961147412153840149680242557985908995809048551221644873177995110096019076374477226711726227375433582742008629075882685808687037270513381674398983431771873413171007802858779826636456553422666594696160434912889687366809422362323098842376241106817547494258021760695957542624512697677068291281565048240876291L}
    priv = {'q': 127510086586749453567799675596482584700119712166804610136675474020193774465506501935103908949613959009028843690899095886887860704939602053795056919145992502189299279551046119412431048933682829194027292286391881720953725313701002889336230082039589574759084409760771330879839666061485599604898295147789162565581L, 'p': 9974300475780491774592969816282305920451245210127658147897766984281371055106368142189687017160402771545023808051471049250797688978492747084656089884206463L, 'd': 91496663593314716159313293929776866666044062194917686206226063395450701615718971977693997683346745354801096056455311995859978719977946286583458836026650416256588542712810899622593278344299892191455617644449970415941495863147311339234008465957157377596651198482790211913515212981736096507080300883685669889045L}
    pub = {'e': 65537L, 'n': 127510086586749453567799675596482584700119712166804610136675474020193774465506501935103908949613959009028843690899095886887860704939602053795056919145992502189299279551046119412431048933682829194027292286391881720953725313701002889336230082039589574759084409760771330879839666061485599604898295147789162565581L}
    pair = MixedKeyPair(pub=pub,priv=priv,size=1024)
    import time
    #pair = MixedKeyPair(size=1024)
    public = pair.publicKey
    private = pair.privateKey
    print public.key, private.key
    t = time.time()
    c = public.encrypt('this are 16 chrs' * 25)
    print c
    print private.decrypt(c)
    print time.time() - t




