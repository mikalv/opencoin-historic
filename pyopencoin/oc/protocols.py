"""
Protocol have states, which are basically methods that consume messages, do
something and return messages. The states are just methods, and one state
might change the state of its protocol to another state. 

A protocol writes to a transport, using Transport.write. It receives messages
from the transport with Protocol.newMessage.

A state (a protocol method) returns messages, it does not write directly back
to a transport (XXX not sure about this, what if a state needs to communicate
with another enity). Instead newMessage by default writes back to the transport.
(XXX maybe the transport could take the returned message, and write it up its own,
ah write method?)

Before returning the message, the state should set the protocols state to the next
state (sounds a bit ackward, its easy, check the states code)
"""

from messages import Message
    

class Protocol:
    """A protocol ties messages and actions togehter, it is basically one side
       of an interaction. E.g. when A exchanges a coin with B, A would use the
       walletSenderProtocol, and B the walletRecipientProtocol."""

    def __init__(self):
        'Set the initial state'
        
        self.state = self.start
        self.result = None

    def setTransport(self,transport):
        'get the transport we are working with'
        
        self.transport = transport
        
    def start(self,message):
        'this should be the initial state of the protocol'
       
        pass

    def goodbye(self,message):
        self.state = self.finish
        return Message('GOODBYE')

    def finish(self,message):
        'always the last state. There can be other final states'        
        return Message('finished')
                    
    def newMessage(self,message):
        'this is used by a transport to pass on new messages to the protocol'

        out = self.state(message)
        self.transport.write(out)
        return out

    def newState(self,method):
        self.state = method

    def initiateHandshake(self,message):    
        self.newState(self.firstStep)
        return Message('HANDSHAKE',{'protocol': 'opencoin 1.0'})


class answerHandshakeProtocol(Protocol):


    def __init__(self,**mapping):
        Protocol.__init__(self)
        self.mapping = mapping

    def start(self,message):

        if message.type == 'HANDSHAKE':
            if message.data['protocol'] == 'opencoin 1.0':
                self.newState(self.dispatch)
                return Message('HANDSHAKE_ACCEPT')
            else:
                self.newState(self.goodbye)
                return Message('HANDSHAKE_REJECT','did not like the protocol version')
        else:
            return Message('PROTOCOL_ERROR','please do a handshake')


    def dispatch(self,message):        
        self.result = message
        nextprotocol = self.mapping[message.type]
        self.transport.setProtocol(nextprotocol)
        m = nextprotocol.newMessage(message)
        #print 'here ', m
        #return m

############################### Spending coins (w2w) ########################################


class CoinSpendSender(Protocol):
    """
    >>> css = CoinSpendSender([1,2],'foobar')
    >>> css.state(Message(None))
    <Message('HANDSHAKE',{'protocol': 'opencoin 1.0'})>
    >>> css.state(Message('HANDSHAKE_ACCEPT'))
    <Message('SUM_ANNOUNCE',['...', 3, 'foobar'])>
    >>> css.state(Message('SUM_ACCEPT'))
    <Message('COIN_SPEND',['...', [1, 2], 'foobar'])>
    >>> css.state(Message('COIN_ACCEPT'))
    <Message('GOODBYE',None)>
    >>> css.state(Message('Really?'))
    <Message('finished',None)>
    """
    def __init__(self,coins,target):

        self.coins = coins
        self.amount = sum(coins)
        self.target = target
        
        import crypto,base64
        id = crypto.Random().getRandomString(128) #XXX is that a good enough id?
        self.transaction_id = base64.b64encode(id)

        Protocol.__init__(self)
        self.state = self.initiateHandshake

    def firstStep(self,message):       
        self.state = self.spendCoin
        return Message('SUM_ANNOUNCE',[self.transaction_id,
                                       self.amount,
                                       self.target])


    def spendCoin(self,message):
        if message.type == 'SUM_ACCEPT':
            self.state = self.goodbye            
            return Message('COIN_SPEND',[self.transaction_id,
                                         self.coins,
                                         self.target])

    def goodbye(self,message):
        if message.type == 'COIN_ACCEPT':
            self.state = self.finish
            return Message('GOODBYE')


class CoinSpendRecipient(Protocol):
    """
    >>> csr = CoinSpendRecipient()
    >>> csr.state(Message('SUM_ANNOUNCE',['123',12,'a book']))
    <Message('SUM_ACCEPT',None)>
    >>> csr.state(Message('COIN_SPEND',['123', [1, 2], 'foobar']))
    <Message('COIN_ACCEPT',None)>
    >>> csr.state(Message('Goodbye',None))
    <Message('GOODBYE',None)>
    >>> csr.state(Message('foobar'))
    <Message('finished',None)>
    """
    
    def __init__(self,issuer_transport = None):
        self.issuer_transport = issuer_transport
        Protocol.__init__(self)

    def start(self,message):
        if message.type == 'SUM_ANNOUNCE':
            #get some feedback from interface somehow
            if 1:
                self.transaction_id = message.data[0]
                self.sum = message.data[1]
                self.target = message.data[2]

                self.state = self.handleCoins
                return Message('SUM_ACCEPT')
            else:                
                self.state=self.goodbye
            return Message('SUM_REJECT')
        else:
            self.state = self.goodbye
            return Message('Expected something else')

    def handleCoins(self,message):
        if message.type == 'COIN_SPEND':
            self.state = self.goodbye
            return Message('COIN_ACCEPT')


############################### Minting key exchange ########################################



class fetchMintingKeyProtocol(Protocol):
    """
    Used by a wallet to fetch the mints keys, needed when 
    creating blanks
       
    ??? Should it be suitable to fetch more than one denomination at a time?
    Maybe all the keys?

    Lets fetch by denomination

    >>> fmp = fetchMintingKeyProtocol(denomination=2)
    >>> fmp.state(Message(None))
    <Message('HANDSHAKE',{'protocol': 'opencoin 1.0'})>

    >>> fmp.state(Message('HANDSHAKE_ACCEPT'))
    <Message('MINTING_KEY_FETCH_DENOMINATION',2)>

    >>> fmp.state(Message('MINTING_KEY_PASS','foobar'))
    <Message('GOODBYE',None)>


    And now by keyid

    >>> fmp = fetchMintingKeyProtocol(keyid='abc')
    >>> fmp.state(Message(None))
    <Message('HANDSHAKE',{'protocol': 'opencoin 1.0'})>

    >>> fmp.state(Message('HANDSHAKE_ACCEPT'))
    <Message('MINTING_KEY_FETCH_KEYID','abc')>

    >>> fmp.state(Message('MINTING_KEY_PASS','foobar'))
    <Message('GOODBYE',None)>


    Lets have some problems a failures (we set the state
    to getKey to resuse the fmp object and save a couple
    of line)

    >>> fmp.newState(fmp.getKey)
    >>> fmp.state(Message('MINTING_KEY_FAILURE',))
    <Message('GOODBYE',None)>
   
    Now lets break something
    
    >>> fmp.newState(fmp.getKey)
    >>> fmp.state(Message('FOOBAR'))
    <Message('PROTOCOL_ERROR','send again')>
    
    """
    
    
    def __init__(self,denomination=None,keyid=None):
        
        self.denomination = denomination
        self.keyid = keyid
        self.keycert = None

        Protocol.__init__(self)

    def start(self,message):
        self.newState(self.requestKey)
        return Message('HANDSHAKE',{'protocol':'opencoin 1.0'})

    def requestKey(self,message):
        """Completes handshake, asks for the minting keys """

        if message.type == 'HANDSHAKE_ACCEPT':
            
            if self.denomination:
                self.newState(self.getKey)
                return Message('MINTING_KEY_FETCH_DENOMINATION',self.denomination)
            elif self.keyid:
                self.newState(self.getKey)
                return Message('MINTING_KEY_FETCH_KEYID',self.keyid) 

        elif message.type == 'HANDSHAKE_REJECT':
            self.newState(self.finish)
            return Message('GOODBYE')

        else:
            return Message('PROTOCOL ERROR','send again')

    def getKey(self,message):
        """Gets the actual key"""

        if message.type == 'MINTING_KEY_PASS':
            self.keycert = message.data
            self.newState(self.finish)
            return Message('GOODBYE')

        elif message.type == 'MINTING_KEY_FAILURE':
            self.reason = message.data
            self.newState(self.finish)
            return Message('GOODBYE')
        
        else:
            return Message('PROTOCOL_ERROR','send again')



class giveMintingKeyProtocol(Protocol):
    """An issuer hands out a key. The other side of fetchMintingKeyProtocol.
    >>> from entities import Issuer
    >>> issuer = Issuer()
    >>> issuer.createKeys(512)
    >>> pub1 = issuer.createSignedMintKey('1','now','later','much later')
    >>> gmp = giveMintingKeyProtocol(issuer)
    
    >>> gmp.state(Message('HANDSHAKE',{'protocol': 'opencoin 1.0'}))
    <Message('HANDSHAKE_ACCEPT',None)>

    >>> m = gmp.state(Message('MINTING_KEY_FETCH_DENOMINATION','1'))
    >>> m == Message('MINTING_KEY_PASS',pub1.toPython())
    True

    >>> gmp.newState(gmp.giveKey)
    >>> m = gmp.state(Message('MINTING_KEY_FETCH_KEYID',pub1.key_identifier))
    >>> m == Message('MINTING_KEY_PASS',pub1.toPython())
    True

    >>> gmp.newState(gmp.giveKey)
    >>> gmp.state(Message('MINTING_KEY_FETCH_DENOMINATION','2'))
    <Message('MINTING_KEY_FAILURE','no key for that denomination available')>
   

    >>> gmp.newState(gmp.giveKey)
    >>> gmp.state(Message('MINTING_KEY_FETCH_KEYID','non existient id'))
    <Message('MINTING_KEY_FAILURE','no such keyid')>

    >>> gmp.newState(gmp.giveKey)
    >>> gmp.state(Message('bla','blub'))
    <Message('MINTING_KEY_FAILURE','wrong question')>

    """

    def __init__(self,issuer):
        
        self.issuer = issuer
        Protocol.__init__(self)


    def start(self,message):

        if message.type == 'HANDSHAKE':
            if message.data['protocol'] == 'opencoin 1.0':
                self.newState(self.giveKey)
                return Message('HANDSHAKE_ACCEPT')
            else:
                self.newState(self.goodbye)
                return Message('HANDSHAKE_REJECT','did not like the protocol version')
        else:
            return Message('PROTOCOL_ERROR','please do a handshake')


    def giveKey(self,message):
    
        self.newState(self.goodbye)

        error = None
        if message.type == 'MINTING_KEY_FETCH_DENOMINATION':
            try:
                key = self.issuer.getKeyByDenomination(message.data)            
            except 'KeyFetchError':                
                error = 'no key for that denomination available'
        
        elif message.type == 'MINTING_KEY_FETCH_KEYID':                
            try:
                key = self.issuer.getKeyById(message.data)                
            except 'KeyFetchError':                
                error = 'no such keyid'
        
        else:
            error = 'wrong question'

        if not error:            
            return Message('MINTING_KEY_PASS',key.toPython())
        else:
            return Message('MINTING_KEY_FAILURE',error)

############################### For testing ########################################

class WalletSenderProtocol(Protocol):
    """
    This is just a fake protocol, just showing how it works

    >>> sp = WalletSenderProtocol(None)
   
    It starts with sending some money
    >>> sp.state(Message(None))
    <Message('sendMoney',[1, 2])>
    
    >>> sp.state(Message('Foo'))
    <Message('Please send a receipt',None)>

    Lets give it a receipt
    >>> sp.state(Message('Receipt'))
    <Message('Goodbye',None)>

    >>> sp.state(Message('Bla'))
    <Message('finished',None)>

    >>> sp.state(Message('Bla'))
    <Message('finished',None)>

    """

    def __init__(self,wallet):
        'we would need a wallet for this to work'

        self.wallet = wallet
        Protocol.__init__(self)

    def start(self,message):
        'always set the new state before returning'
        
        self.state = self.waitForReceipt
        return Message('sendMoney',[1,2])

    def waitForReceipt(self,message):
        'after sending we need a receipt'

        if message.type == 'Receipt':
            self.state=self.finish
            return Message('Goodbye')
        else:
            return Message('Please send a receipt')

class WalletRecipientProtocol(Protocol):

    def __init__(self,wallet=None):
        self.wallet = wallet
        Protocol.__init__(self)

    def start(self,message):
        if message.type == 'sendMoney':
            if self.wallet:
                self.wallet.coins.extend(message.data)
            self.state=self.Goodbye
            return Message('Receipt')
        else:
            return Message('Please send me money, mama')

    def Goodbye(self,message):
        self.state = self.finish
        return Message('Goodbye')

if __name__ == "__main__":
    import doctest,sys
    if len(sys.argv) > 1 and sys.argv[-1] != '-v':
        name = sys.argv[-1]
        gb = globals()
        verbose = '-v' in sys.argv 
        doctest.run_docstring_examples(gb[name],gb,verbose,name)
    else:        
        doctest.testmod(optionflags=doctest.ELLIPSIS)
