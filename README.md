1. download sa diri nga site sng "git-scm.com"

2. installation:

> Select "Use Visual Studio Code as Git's default editor"

> Choose "Git from the command line and also from 3rd-party software"

> Use all other default options

3. sa inyu nga main directory (run sa terminal):

> git config --global user.name "username nyu"
> git config --global user.email "gmail.acc nyu"


4. sa inyu nga main directory (run sa terminal): 
> git clone https://github.com/Chottomatto/cpv7-system.git

5. redirect sa folder (run sa terminal)
> cd cpv7-system 

6. ubra sang virtual environment (run sa terminal)

> python -m venv .venv

(kung d mag gana)

> press & hold (ctrl lshift p)
    > python: Select interpreter
    > create virual env
    > venv


6.a
> .venv\Scripts\activate

6.b
> pip install -r requirements.txt
(kung may mag error)
> manu manu install ang sa sulod sng requirements.txt
example:
pip install tensorflow (pwede sugpunon sila as long may space kada next dependency)






Paano mag run sng system?

1. ubra .env file sa root sng system, tas sa sulod sng .env:
> NEON_DB_URL=inyu nga connection string sa neon db

(kung wala pa kamu neon db)

    > search google neondb
    > log in gamit git hub acc
    >ubra project (default tanan except sa location, Singapore ang ibutang)
    >pag tapos click connect may makita kada sa dalom sng connection string
    >sample sang connection string: psql 'postgresql://neondb_owner:npg_ZQkhAex6i2SD@ep-divine-silence-a18dz5k2-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
    > i copy lang ang ari: postgresql://neondb_owner:npg_ZQkhAex6i2SD@ep-divine-silence-a18dz5k2-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
    >paste sa .env file

1b. ubra sng ml folder sa root sng system, tas sa sulod ya ubra pagid ubra sng models nga folder.
    dri ni masulod ang i train naton nga ml


2. train ang ml (run sa terminal)
> python backend/ml/train.py

3. pag tapos train (run sa terminal)
> python start_crawl.py

4. pag tapos crawl/score (run sa terminal)
> python run_frontend.py




