# Formal Memory Package A — Runtime Freeze V1

Code authority: `9d4e4b853fb62757ed8c709d76d14b80bc3fd357`

Code Approval: `b38b7a83af706faa29089f1e0077af9438209e29`

Served scientific model alias: `P4-R1-Q2-BAD-TRAIN17`

Runtime identity is frozen by:
- PolicyCondition semantic runtime SHA: `215bbe3981668181c8b2eb51c4568af944512f7c20c4504ad75faa012cc83faa`;
- exact SELECT v2 SHA256SUMS file SHA: `63c850a9a616dad2029a7224221d603bc0cd9ebf1427dc86b377f834bce0cdb5`;
- runtime descriptor file SHA: `215bbe3981668181c8b2eb51c4568af944512f7c20c4504ad75faa012cc83faa`;
- historical Train17 model-identity smoke SHA: `2f501c2a76f2c01586e95546c7afc27a0dd26dd04a51b5108dcab16f7d925dc8`.

Additional authority:
- base model revision: `aa8e72537993ba99e69dfaafa59ed015b17504d1`;
- adapter bundle SHA: `b296f2254b1fa1f2e141dffd3f6b5af903f839df4790ffcb245fd8dd57773ace`;
- tokenizer chat-template SHA: `cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f`;
- decoding contract SHA: `7a95985000ac80895fe194a240d50301ea1ab51a914eddedec501b3261812e37`;
- vLLM: `0.11.0`;
- context window: `32768`;
- HF snapshot storage audit SHA: `de187977bc332020504cdb5a42033640bd7460050ea782758575d08f37c34aad`;
- runtime authority file SHA: `080336f7bf579849c90b7f8320e3e6a0c2047b8eacddf382bf24677fd1d5b885`.

The runtime descriptor is byte-frozen by SELECT v2 and does not need to contain its
own externally assigned semantic hash as a literal JSON value.

Hugging Face snapshot symlinks are accepted only when they resolve to regular files
under the exact model-cache blobs root. Project-owned frozen artifacts remain
non-symlink-only.

The decoding contract is mechanically checked against Code-Approved
E1PolicyRequestV1 fixed wire fields.

No model inference, ALFWorld scientific execution, Memory-ON execution, or scheduler
submission occurred during this freeze.

Next gate: explicit Formal A0 scientific execution approval.
