# Daemons

==========

düzenli aralıklarla kontrol etmen gereken şeyler

1. event

EventDaemon(interval, topic, contract_address) x1

2. block

BlockDaemon() x1 => triggers:[theft,]

3. state x1 (theftTrigger, EventDaemon, etc.)

# Actions

============

1. Send tx
2. send tx params to watcher server
3. get email
4. get telegram message
5. save to database

1. getEventDetails
2. falan

# Notes

============
Telescope :
-> birden fazla daemon çalıştırıp, her daemon loopu bitince de triggerları çalıştırıyor.
-> sonra : içerisine bi tane config alıyo ve ona göre customize ediyor.

.

# Planning

============

1. telescope => daemonları alıyor, triggerları alıyor.
2. daemon  
   1. logicinin içerisinde triggerı gömebilirsin
   2. stateful checkpoint logici yazılıcak.
      1. belki daemon classı statefuldan inherit edilmeli
      2. verfiy function olarak alınabilir.
   3. sonra daemon lar yazılıcak.
3. trigger
4. yeri geldikçe de actionları yazarız
5. yml ve config kullanıcak şekilde değiştir.
   1. bu sırada logların actionlara göre nasıl işlenmesi gerektiği de stateful classında olmalı.
6. log ekranı yazılıcak

TASKS:

1. UpdateVerificationIndex:     uint256 validatorVerificationIndex, bytes[]  alienatedPubkey
2. reportBeacon:     bytes32 priceMerkleRoot, bytes32 balanceMerkleRoot, uint256 allValidatorsCount
3. regulateOperators:     uint256[] feeThefts, bytes[] proofs

Daemons:

1. EVENT ->
2. BLOCK -> planets{price, validators}
3. BLOCK

Note: eğer block recipient withdrawal pool değilse, biz de withdrawal pool a herhangi bir transaction yapılmış mı diye bakarız. hmm bu sıkıntı yaratabilir.
Onun yerine relayların listesini tutabiliriz.

THEN a whole new stuff starts to pop up with EventDaemon which I don't even know what it does tbh but will hopefully figure out soon.
Current objective is to finish the update verification index? -> on every x block check for events.

### diff

1. CLI kısmını daha sonra geliştirelim.
2. Config.py can be modifiable.
3. Stateful Objesinin tasklarını sona bırakabiliriz.
4. Daemon -> trigger -> action

##  checkpoint / log / email -> MONİTORING AND EVENT HANDLING

-> loglar farklı DIR de dursun.
   -> LOGGING => buna da daha sonra bakalım.
   -> action ve run logları var ama herşeyi kaydetmiyoruz (**error handling parçası**)

## typing, comments, file/variable naming (snake_case)

- verificationTrigger
- priceTrigger, balanceTrigger -> price / balance,
- Feetheft & MEV
- stateDaemon

TODO_comment : Please remove any unnecessary data at the end.
Lets keep anything that can be useful for now.

<!-- eğer tek 1 tane stateful kullanıp birden fazla database üzerinde çalışırsak, bir takım optimizasyonlar yapabiliriz. -->
Kİ BUNU DA AŞIRI KOLAY Bİ ŞEKİLDE REGİSTER_STATE fonksiyonu ekleyerek yapabiliriz. aslında çok mantıklı. tek 1 tane olucak bütün stateleri o handle edicek. neden olmasın.
<!-- -> GEREK YOKK -->

TODO_task
todo_later
TODO_comment
TODO_unrelated
TODO_finally

1. verify + optimize
2. Error Handling
3. Comment
4. Logging + Notifications
