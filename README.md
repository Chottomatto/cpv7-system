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

1.a. ubra .env file sa root sng system, tas sa sulod sng .env:
> NEON_DB_URL=inyu nga connection string sa neon db

(kung wala pa kamu neon db)

    > search google neondb

    > log in gamit git hub acc

    > ubra project (default tanan except sa location, Singapore ang ibutang)

    > pag tapos click connect may makita kada sa dalom sng connection string

    > sample sang connection string: psql 'postgresql://
    neondb_owner:npg_ZQkhAex6i2SD@ep-divine-silence-a18dz5k2-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

    > i copy lang ang ari: postgresql://neondb_owner:npg_ZQkhAex6i2SD@ep-divine-silence-a18dz5k2-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require

    > paste sa .env file

1.b. ubra sng ml folder sa root sng system, tas sa sulod ya ubra pagid ubra sng models nga folder.
    dri ni masulod ang i train naton nga ml


2. train ang ml (run sa terminal)
    > python backend/ml/train.py

3. pag tapos train (run sa terminal)
    > python start_crawl.py

4. pag tapos crawl/score (run sa terminal)
    > python run_frontend.py



FILE NGA ILISLAN BASED SA SDG (check sdg metrics)

i identify nyu lang kung diin nga metrics ang pwede maclassify (ignore lang ang sdg metrics nga ga kuha sng real numbers kay d na kaya basahun sng ml, kung parti naman sa publication, citation etc.. d nyu na pag dal-a) 


> backend/config.py

    > CATEGORY_WEIGHTS = {
        'public_resource': 0.05,
        'public_events': 0.05, 
        'vocational_training': 0.05,
        'education_outreach': 0.05,
        'access_policy': 0.068,
        'teaching_qualifications': 0.154,
        'first_generation_students': 0.308
    }

> backend/ml/model.py

    > self.categories = [
            'public_resource', 'public_events', 'vocational_training',
            'education_outreach', 'access_policy'
        ]


> backend/ml/train.py

    > CATEGORIES = [
    'public_resource', 'public_events', 'vocational_training',
    'education_outreach', 'access_policy'
]


> training_data/classification_training_data.csv
(ang mga classes i adjust nyu based kung ano sa inyu nga config.py (ang configuration_weight))