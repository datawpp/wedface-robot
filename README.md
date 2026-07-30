# WedFace face-scan robot 🤖

Ye robot **GitHub ke free servers** par chalta hai aur wedface.in ke saare
LIVE weddings ke photos ka face-scan **khud** karta rehta hai — koi computer
khula rakhne ki zaroorat nahi.

- Har **30 minute** me khud chalta hai
- Naya **selfie ya wedding** aate hi site ise **turant** bhi jaga deti hai
  (Superadmin → Settings me GitHub token daala ho to)
- Sirf **LIVE** weddings scan hoti hain (jo photographer ke slots me ON hain) —
  isliye minutes kabhi waste nahi hote

## Setup (ek baar, ~10 minute)

1. **github.com** par account banao (free) — agar hai to login.

2. Naya repository banao: upar-right **+** → **New repository**
   - Name: `wedface-robot`
   - **Public** rakho — public repos par GitHub Actions ke minutes UNLIMITED free
     hain (token repo me NAHI hota, sirf Secrets me — isliye public safe hai)
   - **Create repository**

3. Is folder ki saari cheezein upload karo:
   repo page par **uploading an existing file** → ye files drag karo:
   - `scan.py`
   - `requirements.txt`
   - `.github` folder (poora — isme workflows/scan.yml hai)

   > Browser se `.github` folder upload na ho to: **Add file → Create new file**,
   > naam me type karo `.github/workflows/scan.yml` aur scan.yml ka content
   > paste kar do.

4. **Secret token** daalo:
   repo me **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `WF_TOKEN`
   - Value: WedFace **Superadmin → Settings → Robot token** wala token
   - **Add secret**

   > Site ka address wedface.in nahi hai? To wahi jagah **Variables** tab me
   > `WF_BASE` naam ka variable banao, value me apna URL (https://apnisite.com).

5. **Actions tab** kholo → "enable workflows" pooche to enable karo →
   left me **face-scan** → **Run workflow** (pehla run haath se chala ke dekh lo).

Bas! Ab robot khud chalta rahega.

## Instant scan (optional, recommended)

Site se robot ko turant jagane ke liye:
1. GitHub → apni photo (upar-right) → **Settings → Developer settings →
   Personal access tokens → Fine-grained tokens → Generate new token**
2. Repository access: **Only select repositories** → `wedface-robot`
3. Permissions → Repository permissions → **Contents: Read and write**
4. Token copy karke WedFace **Superadmin → Settings → GitHub robot** me
   repo (`aapkaUsername/wedface-robot`) + token save karo.

Ab guest selfie dalte hi robot seconds me chal padega (30 min wait nahi).

## Kaise pata chalega ki chal raha hai?

- GitHub **Actions** tab — har run ka log (kitne photos, kitne faces)
- WedFace **Superadmin → Scans** — robot ka last-seen + har wedding ka status
- Logs me kabhi naam/code/URL nahi chhapte — sirf wedding/folder numbers
  (public repo ho to bhi privacy safe)

## Notes

- **Public repo = unlimited free minutes.** Private rakhna ho to bhi chalega —
  free 2,000 min/month me lagbhag 30-50 hazaar photos ka scan aa jata hai.
- Pehla run thoda lamba (~2 min extra) — InsightFace model download hota hai,
  phir cache ho jata hai.
- 6000 photos wali nayi wedding ka poora scan kuch ghante leta hai (robot
  45-min ke tukdon me karta hai, checkpoint ke saath) — link turant share kar
  sakte ho, guest ke matches scan ke saath-saath badhte jaate hain.
- GitHub 60 din repo me koi activity na ho to schedule pause kar deta hai
  (email aata hai) — README me ek space add karke commit kar dena, phir chalu.
- Robot ke paas site ka password/database NAHI hota — sirf scan-only token.
