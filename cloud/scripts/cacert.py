from datetime import datetime
from datetime import timedelta
from datetime import timezone

import OpenSSL.crypto as openssl

now = datetime.utcnow()
now = now.replace(tzinfo=timezone.utc)
expires = now + timedelta(days=365)

cacert_key = openssl.PKey()
cacert_key.generate_key(openssl.TYPE_RSA, 2048)
cacert_key_pem = openssl.dump_privatekey(openssl.FILETYPE_PEM, cacert_key)
cacert_key_pem = cacert_key_pem.decode('utf-8')
print(f'cacert_key_pem = {cacert_key_pem}')

cacert_csr = openssl.X509Req()
cacert_subject = cacert_csr.get_subject()
cacert_subject.C = 'US'
cacert_subject.CN = 'test'
cacert_csr.set_pubkey(cacert_key)

cacert_crt = openssl.X509()

cacert_crt.set_notBefore(now.strftime('%Y%m%d%H%M%SZ').encode('utf-8'))
cacert_crt.set_notAfter(expires.strftime('%Y%m%d%H%M%SZ').encode('utf-8'))
cacert_crt.set_issuer(openssl.X509Name(cacert_subject))
cacert_crt.set_subject(openssl.X509Name(cacert_subject))
cacert_crt.set_pubkey(cacert_csr.get_pubkey())
cacert_crt.add_extensions([openssl.X509Extension(b'basicConstraints', True, b'CA:TRUE,pathlen:0')])
cacert_crt.sign(cacert_key, 'sha256')
cacert_key_pem = openssl.dump_certificate(openssl.FILETYPE_PEM, cacert_crt)
cacert_key_pem = cacert_key_pem.decode('utf-8')
print(f'cacert_crt_pem = {cacert_key_pem}')
# with open('cacert.pem', 'w') as f:
#     f.write(cacert_key_pem)

verification_key = openssl.PKey()
verification_key.generate_key(openssl.TYPE_RSA, 2048)

verification_csr = openssl.X509Req()
verification_subject = verification_csr.get_subject()
if cacert_subject.C: verification_subject.C = cacert_subject.C
if cacert_subject.ST: verification_subject.ST = cacert_subject.ST
if cacert_subject.L: verification_subject.L = cacert_subject.L
if cacert_subject.O: verification_subject.O = cacert_subject.O
verification_subject.CN = 'paste-aws-iot-registration-code-here'
verification_csr.set_pubkey(verification_key)

verification_crt = openssl.X509()
verification_crt.set_notBefore(now.strftime('%Y%m%d%H%M%SZ').encode('utf-8'))
verification_crt.set_notAfter(expires.strftime('%Y%m%d%H%M%SZ').encode('utf-8'))
verification_crt.set_issuer(openssl.X509Name(cacert_subject))
verification_crt.set_subject(openssl.X509Name(verification_subject))
verification_crt.set_pubkey(verification_csr.get_pubkey())
verification_crt.sign(cacert_key, 'sha256')
verification_crt_pem = openssl.dump_certificate(openssl.FILETYPE_PEM, verification_crt)
verification_crt_pem = verification_crt_pem.decode('utf-8')
print(f'verification_crt_pem = {verification_crt_pem}')
# with open('verif.pem', 'w') as f:
#     f.write(verification_crt_pem)
