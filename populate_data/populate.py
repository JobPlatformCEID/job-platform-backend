import sys
import os
import django
import csv
import random

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.files import File
from users.models import User, CandidateProfile, EmployerProfile, WorkExperience, Education, Skill
from reviews.models import Review
from jobs.models import JobPosting
from social.models import Post, PostImage, Comment, Like

# paths
BASE_DIR             = os.path.dirname(os.path.abspath(__file__))
EMPLOYERS_CSV        = os.path.join(BASE_DIR, 'employers.csv')
CANDIDATES_CSV       = os.path.join(BASE_DIR, 'candidates.csv')
PHOTOS_DIR           = os.path.join(BASE_DIR, 'employers')
CANDIDATE_PHOTOS_DIR = os.path.join(BASE_DIR, 'candidates')
MEMES_DIR            = os.path.join(BASE_DIR, 'memes')

# review content by score threshold
REVIEW_MESSAGES = [
    # reviews[0] → score 0-2  (negative)
    "Honestly disappointed.\nThe work environment felt chaotic and management was unresponsive.\nWould not recommend.",
    # reviews[1] → score 3    (neutral)
    "Decent place to work.\nNothing exceptional but the team was okay and the pay was fair.",
    # reviews[2] → score 4-5  (positive)
    "Fantastic company!\nGreat culture, supportive management, and real opportunities to grow.\nHighly recommend.",
]

def get_review_message(score):
    if score <= 2:
        return REVIEW_MESSAGES[0]
    elif score == 3:
        return REVIEW_MESSAGES[1]
    else:
        return REVIEW_MESSAGES[2]

# employer descriptions
EMPLOYER_DESCRIPTIONS = {
    'Amazon': (
        "Amazon is a global leader in e-commerce and cloud computing.\n"
        "We obsess over customers and push the boundaries of technology every single day.\n"
        "From AWS to Prime, we build services that power the modern world."
    ),
    'Google': (
        "Google's mission is to organize the world's information and make it universally accessible.\n"
        "We build products that help billions of people every day.\n"
        "From Search to Android, our teams work on problems that matter at global scale."
    ),
    'Netflix': (
        "Netflix is the world's leading streaming entertainment service.\n"
        "We believe in freedom and responsibility — giving our team the tools to do their best work.\n"
        "No rules, just results. We trust you to act in Netflix's best interest."
    ),
    'Vought International': (
        "Vought International is a Fortune 500 conglomerate and defense contractor.\n"
        "We develop innovative solutions across aerospace, biotech, and security.\n"
        "Our supes protect the world. Our engineers make it possible."
    ),
    'Εθνική Ασφαλιστική': (
        "Η Εθνική Ασφαλιστική είναι η μεγαλύτερη ασφαλιστική εταιρεία στην Ελλάδα.\n"
        "Με δεκαετίες εμπειρίας και αξιοπιστίας, προστατεύουμε αυτό που σας αξίζει.\n"
        "Ασφάλεια ζωής, υγείας και περιουσίας για κάθε Έλληνα."
    ),
    'Microslop': (
        "Microslop builds enterprise software that nobody asked for but everyone is forced to use.\n"
        "We ship bugs fast and call them features.\n"
        "Our support team is available 9-5, Monday to Monday."
    ),
    'TikTok': (
        "TikTok is the leading destination for short-form mobile video.\n"
        "Our mission is to inspire creativity and bring joy to people around the world.\n"
        "Join us and help shape what a billion people watch tomorrow."
    ),
}

# candidate bios
CANDIDATE_BIOS = {
    'richardhendricks': (
        "Obsessive engineer with a passion for compression algorithms.\n"
        "Awkward in meetings, brilliant in code.\n"
        "If I can't make it middle-out, I'm not interested."
    ),
    'erlichbachman': (
        "Visionary entrepreneur and incubator owner.\n"
        "I don't just think outside the box — I built the box, disrupted it, and monetized the rubble.\n"
        "Available for board seats, keynotes, and spiritual guidance."
    ),
    'bighead': (
        "I've been at Hooli for years.\n"
        "I'm not totally sure what I did there but people seemed to like me.\n"
        "Looking for my next big thing."
    ),
    'gilfoyle': (
        "Systems architect and borderline anarchist.\n"
        "I secure things, break things, and occasionally tolerate people.\n"
        "Satanist. Not a joke."
    ),
    'dinesh': (
        "Full stack developer with opinions about everything and code to back most of them up.\n"
        "Yes I can do that in React. No I won't use Angular.\n"
        "Ask me about my watch."
    ),
    'jareddunn': (
        "Operations enthusiast who finds joy in process optimization and spreadsheet hygiene.\n"
        "Former Hooli, former orphan, full-time team player.\n"
        "I will bring baked goods to every standup."
    ),
    'monicahall': (
        "Data-driven finance professional who actually reads the term sheets.\n"
        "Looking for companies that build things worth funding.\n"
        "No, I will not sign that NDA before the pitch."
    ),
    'gavinbelson': (
        "Visionary. Leader. Guru. I've been called all three.\n"
        "I coined the phrase 'I don't want to live in a world that I've created.'\n"
        "Still working on that."
    ),
    'russ': (
        "Three commas. That's all I'll say.\n"
        "Looking for the next idea that adds a comma.\n"
        "I only take meetings on yachts."
    ),
    'lauriebream': (
        "Data scientist and venture capitalist with a clinical approach to decision making.\n"
        "I process information. I also occasionally feel things.\n"
        "Pivot or die."
    ),
    'jackbarker': (
        "Results-oriented executive with extensive experience turning scrappy teams into enterprise-grade operations.\n"
        "I bring structure, process, and a strong foosball game.\n"
        "Let's build something scalable."
    ),
    'endframe': (
        "ML engineer specializing in deep learning and compression.\n"
        "Currently exploring opportunities after EndFrame's acquisition.\n"
        "Our algorithm was better. I stand by that."
    ),
    'gilmanguo': (
        "Cloud infrastructure engineer who speaks fluent Kubernetes.\n"
        "I make things scale so you don't have to think about it.\n"
        "Zero downtime is not a goal, it's a minimum."
    ),
    'rondavm': (
        "Designer who believes great UX is invisible.\n"
        "I solve problems with pixels and empathy.\n"
        "If you can see my work, I haven't finished yet."
    ),
    'henshawt': (
        "Mobile developer who ships clean, performant apps on both iOS and Android.\n"
        "Flutter evangelist. Coffee dependent.\n"
        "Dark mode only."
    ),
    'priyaali': (
        "Backend engineer who loves clean APIs and hates N+1 queries.\n"
        "Django is my hammer and everything looks like a nail.\n"
        "SELECT * is a war crime."
    ),
    'wendyzhao': (
        "Full stack developer with a frontend heart.\n"
        "I build things people actually enjoy using.\n"
        "CSS is a programming language and I will die on this hill."
    ),
    'connorwalsh': (
        "Backend engineer specializing in fintech systems.\n"
        "I care deeply about correctness, uptime, and Boston sports.\n"
        "Four nines or bust."
    ),
    'sofiamendez': (
        "Data analyst who turns messy spreadsheets into actionable insights.\n"
        "Athens based, globally minded.\n"
        "Pivot tables don't scare me."
    ),
    'niklasbjorn': (
        "Systems programmer and open source contributor.\n"
        "Rust is my love language.\n"
        "Memory safe or memory sorry."
    ),
    'guilfoyleclone': (
        "Infrastructure-first thinker.\n"
        "If it doesn't scale, it doesn't ship.\n"
        "I have strong opinions about network topology."
    ),
    'bachmanito': (
        "Frontend developer with an eye for design.\n"
        "I make things look good without always knowing why.\n"
        "Tailwind changed my life."
    ),
    'taborhaynes': (
        "Android developer who believes the best apps are the ones users don't have to think about.\n"
        "Jetpack Compose convert.\n"
        "Material You, always."
    ),
    'carenmoody': (
        "UX designer who starts every project with user research and ends it with something beautiful.\n"
        "Figma is my happy place.\n"
        "I will fight for the user."
    ),
    'olgabrandt': (
        "Data analyst with a love for clean visualizations and reproducible research.\n"
        "Python and R in equal measure.\n"
        "A chart without axis labels is a crime."
    ),
    'hamidkarimi': (
        "Backend engineer passionate about distributed systems and high-throughput APIs.\n"
        "CAP theorem keeps me up at night.\n"
        "Eventual consistency is not a personality trait."
    ),
    'yusufadeyemi': (
        "Frontend developer building fast, accessible web experiences for African and global markets.\n"
        "Performance matters when bandwidth doesn't.\n"
        "Accessibility is not optional."
    ),
    'alexkowalski': (
        "Java backend developer with deep experience in e-commerce platforms and payment systems.\n"
        "Spring Boot is home.\n"
        "I have strong feelings about checked exceptions."
    ),
    'tanvirsheikh': (
        "Django developer fresh out of university and hungry to build real things.\n"
        "I learn fast and break things responsibly.\n"
        "Open to any stack, loyal to Python."
    ),
    'irenegalvez': (
        "iOS developer crafting native experiences that feel right on every screen size.\n"
        "SwiftUI enthusiast.\n"
        "The back button is a last resort."
    ),
}


def seed():
    print('Seeding from CSV files...')

    # Employers
    employers = []
    with open(EMPLOYERS_CSV, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            user, created = User.objects.get_or_create(
                username=row['username'],
                defaults={
                    'email': row['email'],
                    'role':  'employer',
                }
            )
            if created:
                user.set_password(row['password'])
                user.save()

            company_name = row['company_name']
            profile, _ = EmployerProfile.objects.get_or_create(
                user=user,
                defaults={
                    'company_name': company_name,
                    'description':  EMPLOYER_DESCRIPTIONS.get(company_name, ''),
                    'location':     row['location'],
                    'website':      row['website'],
                }
            )

            photo_path = os.path.join(BASE_DIR, row['photo'])
            if os.path.exists(photo_path) and not user.avatar:
                with open(photo_path, 'rb') as img:
                    filename = os.path.basename(photo_path)
                    user.avatar.save(filename, File(img), save=True)

            employers.append(profile)

    print(f'  {len(employers)} employers created')

    # Candidates
    photo_files = [os.path.join(CANDIDATE_PHOTOS_DIR, f'{i}.png') for i in range(1, 11)]

    candidates = []
    with open(CANDIDATES_CSV, newline='', encoding='utf-8') as f:
        for idx, row in enumerate(csv.DictReader(f)):
            user, created = User.objects.get_or_create(
                username=row['username'],
                defaults={
                    'email':      row['email'],
                    'first_name': row['first_name'],
                    'last_name':  row['last_name'],
                    'role':       'candidate',
                }
            )
            if created:
                user.set_password(row['password'])
                user.save()

            photo_path = photo_files[idx % len(photo_files)]
            if os.path.exists(photo_path) and not user.avatar:
                with open(photo_path, 'rb') as img:
                    filename = os.path.basename(photo_path)
                    user.avatar.save(filename, File(img), save=True)

            profile, _ = CandidateProfile.objects.get_or_create(
                user=user,
                defaults={
                    'phone':    row['phone'],
                    'location': row['location'],
                    'bio':      CANDIDATE_BIOS.get(row['username'], ''),
                }
            )

            for skill_name in row['skills'].split(','):
                skill_name = skill_name.strip()
                if skill_name:
                    Skill.objects.get_or_create(candidate=profile, name=skill_name)

            Education.objects.get_or_create(
                candidate=profile,
                defaults={
                    'institution':     row['education_institution'],
                    'degree':          row['education_degree'],
                    'level':           row['education_level'],
                    'graduation_date': row['graduation_date'] or None,
                }
            )

            WorkExperience.objects.get_or_create(
                candidate=profile,
                title=row['work_title'],
                company=row['work_company'],
                defaults={
                    'start_date':      row['work_start_date'],
                    'end_date':        None,
                    'employment_type': row['work_employment_type'],
                    'description':     'Worked on various projects and collaborated with cross-functional teams.',
                }
            )

            candidates.append(profile)

    print(f'  {len(candidates)} candidates created')

    # Reviews (first 10 candidates → all employers)
    review_count = 0
    for candidate in candidates[:10]:
        for employer in employers:
            score = random.randint(0, 5)
            content = get_review_message(score)
            Review.objects.get_or_create(
                employer=employer,
                owner=candidate.user,
                defaults={
                    'score':   score,
                    'content': content,
                }
            )
            review_count += 1

    print(f'  {review_count} reviews created')

    # Jobs (7 per employer)
    # Each tuple: (title, description, requirements, salary_min, salary_max,
    #              location, is_remote, contract_type)
    JOBS_BY_EMPLOYER = {
        'Amazon': [
            (
                'Backend Engineer',
                'Build and maintain high-throughput microservices that power Amazon\'s order pipeline.\nYou will work closely with infrastructure teams to ensure sub-100ms latency at scale.\nOwnership from design through production is expected.',
                'Python or Java\nExperience with distributed systems\nFamiliarity with AWS',
                3500, 5500, 'Seattle, WA', False, 'full_time',
            ),
            (
                'Cloud Solutions Architect',
                'Design cloud-native architectures for enterprise clients migrating to AWS.\nYou will lead technical discovery sessions and produce reference architectures.\nTravel to client sites is occasional.',
                'AWS certifications preferred\n5+ years infrastructure experience\nStrong communication skills',
                5000, 7500, 'Remote', True, 'full_time',
            ),
            (
                'Data Engineer',
                'Build and own the data pipelines that feed Amazon\'s recommendation engine.\nYou will work with petabyte-scale datasets using Spark and Redshift.\nData quality and pipeline reliability are your primary KPIs.',
                'Apache Spark\nSQL at an advanced level\nPython scripting',
                4000, 6000, 'Seattle, WA', False, 'full_time',
            ),
            (
                'DevOps Engineer',
                'Own CI/CD pipelines and container orchestration for a large product team.\nYou will reduce deployment friction and improve observability across services.\nOn-call rotation is shared across the team.',
                'Kubernetes and Docker\nTerraform or CDK\nExperience with incident response',
                3800, 5800, 'Seattle, WA', False, 'full_time',
            ),
            (
                'Frontend Engineer',
                'Build performant, accessible interfaces for Amazon\'s seller dashboard.\nYou will collaborate with product and design to ship features used by millions of sellers.\nComponent library ownership is part of the role.',
                'React and TypeScript\nAccessibility standards (WCAG)\nPerformance profiling experience',
                3200, 5000, 'Remote', True, 'full_time',
            ),
            (
                'ML Engineer',
                'Train and deploy recommendation models that drive product discovery.\nYou will iterate on feature engineering and A/B test model variants in production.\nClose collaboration with data science and product teams is expected.',
                'PyTorch or TensorFlow\nMLOps experience\nStrong Python skills',
                4500, 7000, 'Seattle, WA', False, 'full_time',
            ),
            (
                'Logistics Operations Intern',
                'Support the last-mile delivery analytics team during a 3-month internship.\nYou will write SQL queries, build dashboards, and present findings to operations managers.\nHands-on exposure to real supply chain data from day one.',
                'Currently enrolled in a relevant degree\nBasic SQL knowledge\nEager to learn',
                1200, 1800, 'Seattle, WA', False, 'internship',
            ),
        ],
        'Google': [
            (
                'Site Reliability Engineer',
                'Maintain the reliability and performance of Google Search infrastructure.\nYou will define SLOs, build alerting systems, and lead postmortems.\nAutomating toil away is a core expectation of the role.',
                'Linux internals\nGo or Python\nExperience with large-scale distributed systems',
                5000, 8000, 'Mountain View, CA', False, 'full_time',
            ),
            (
                'Android Engineer',
                'Build features for the Google Maps Android app used by over a billion people.\nYou will own features end-to-end from architecture to Play Store release.\nPerformance and battery efficiency are first-class concerns.',
                'Kotlin and Android SDK\nJetpack Compose\nExperience shipping production Android apps',
                4500, 7000, 'Mountain View, CA', False, 'full_time',
            ),
            (
                'Research Scientist – NLP',
                'Conduct original research on large language models and publish findings.\nYou will collaborate with product teams to bring research into Google products.\nPublication record and independent research agenda expected.',
                'PhD in ML or related field\nPublications at top venues (NeurIPS, ICML, ACL)\nPyTorch or JAX',
                6000, 9500, 'Remote', True, 'full_time',
            ),
            (
                'Security Engineer',
                'Identify and remediate vulnerabilities across Google\'s web and mobile surfaces.\nYou will conduct threat modelling, red team exercises, and security reviews.\nResponsible disclosure experience is a strong plus.',
                'Web and mobile security\nExperience with CTFs or bug bounty programs\nStrong understanding of OWASP Top 10',
                4800, 7500, 'Mountain View, CA', False, 'full_time',
            ),
            (
                'Product Manager – Google Cloud',
                'Define the roadmap for a Google Cloud developer tooling product.\nYou will gather customer feedback, write PRDs, and work with engineering to ship.\nTechnical background required — you will be in the code with the team.',
                'Technical undergraduate degree\n3+ years PM experience\nCloud infrastructure knowledge',
                5500, 8500, 'Mountain View, CA', False, 'full_time',
            ),
            (
                'UX Designer',
                'Design end-to-end experiences for Google Workspace productivity tools.\nYou will run user research, produce wireframes, and iterate based on data.\nStrong systems thinking and a sharp eye for detail required.',
                'Portfolio demonstrating end-to-end UX process\nFigma proficiency\nExperience with design systems',
                4000, 6500, 'Remote', True, 'full_time',
            ),
            (
                'Software Engineering Intern',
                'Work on a real product team for 12 weeks and ship code to production.\nYou will be assigned a host engineer and a well-scoped project from day one.\nInterns present their work at the end of the program.',
                'Currently enrolled in CS or related degree\nProficiency in at least one language\nGPA 3.5+ preferred',
                2000, 2500, 'Mountain View, CA', False, 'internship',
            ),
        ],
        'Netflix': [
            (
                'Senior Backend Engineer – Streaming',
                'Own the video delivery pipeline that serves 270 million subscribers.\nYou will optimize adaptive bitrate algorithms and reduce rebuffering rates.\nIncident ownership and on-call are part of the job.',
                'Java or Kotlin\nExperience with CDN and video protocols (HLS, DASH)\nHigh-traffic systems background',
                5500, 9000, 'Los Gatos, CA', False, 'full_time',
            ),
            (
                'Data Scientist – Content',
                'Model viewer engagement to inform Netflix\'s content acquisition decisions.\nYou will build predictive models and present findings to content executives.\nYour work directly influences what gets greenlit.',
                'Python and R\nCausal inference experience\nStrong data storytelling skills',
                4500, 7000, 'Los Gatos, CA', False, 'full_time',
            ),
            (
                'iOS Engineer',
                'Build the Netflix iOS app experience for iPhone and iPad.\nYou will work on playback, downloads, and the browse experience.\nPerformance and accessibility are non-negotiable.',
                'Swift and UIKit or SwiftUI\nAVFoundation experience a plus\nApp Store release experience',
                4500, 7000, 'Remote', True, 'full_time',
            ),
            (
                'Platform Engineer – Developer Productivity',
                'Build internal tooling that helps Netflix engineers ship faster and safer.\nYou will own parts of the internal CI/CD platform and developer portal.\nDeveloper empathy is as important as technical skill here.',
                'Kotlin or Go\nKubernetes\nExperience building internal platforms',
                5000, 8000, 'Los Gatos, CA', False, 'full_time',
            ),
            (
                'Security Engineer – AppSec',
                'Embed in product teams to review code, threat-model features, and build secure defaults.\nYou will run pen tests on Netflix apps and APIs.\nShifting security left is the mission.',
                'Application security background\nExperience with SAST/DAST tooling\nScripting in Python',
                4800, 7500, 'Remote', True, 'full_time',
            ),
            (
                'ML Engineer – Recommendations',
                'Train and serve the models behind Netflix\'s recommendation carousel.\nYou will own feature pipelines, model evaluation, and A/B testing infrastructure.\nYour models run for every session of every subscriber.',
                'Python and PyTorch\nRecommendation systems experience\nMLOps and model serving',
                5000, 8500, 'Los Gatos, CA', False, 'full_time',
            ),
            (
                'Finance Analyst',
                'Support Netflix\'s content finance team with budget tracking and variance analysis.\nYou will build models in Excel and present to senior leadership monthly.\nAttention to detail and discretion are essential.',
                'Finance or accounting degree\nAdvanced Excel\nExperience in media finance a plus',
                2800, 4000, 'Los Gatos, CA', False, 'full_time',
            ),
        ],
        'Vought International': [
            (
                'Aerospace Systems Engineer',
                'Design and test structural components for next-generation defense aircraft.\nYou will work alongside program managers and government contractors.\nSecurity clearance will be required after hiring.',
                'Aerospace or mechanical engineering degree\nCAD experience (CATIA or SolidWorks)\nKnowledge of FAA/MIL-SPEC standards',
                4000, 6500, 'New York, NY', False, 'full_time',
            ),
            (
                'Biotech Research Scientist',
                'Conduct research on performance-enhancing compounds for Vought\'s proprietary programs.\nYou will design experiments, analyze results, and write internal technical reports.\nDiscretion and confidentiality are mandatory.',
                'PhD in biochemistry or pharmacology\nLab experience with mammalian cell cultures\nAbility to work under NDA',
                5000, 8000, 'New York, NY', False, 'full_time',
            ),
            (
                'Cybersecurity Analyst',
                'Monitor and protect Vought\'s classified infrastructure from external threats.\nYou will perform threat hunting, incident response, and vulnerability assessments.\nYou will have access to systems most analysts never see.',
                'CISSP or CEH certification preferred\nSIEM experience\nUS citizenship required',
                4200, 6500, 'New York, NY', False, 'full_time',
            ),
            (
                'Backend Developer – Internal Tools',
                'Build internal web applications for Vought\'s operations and logistics teams.\nYou will work in a small team with high autonomy and fast release cycles.\nWhat you build will be seen by very few people and used by thousands.',
                'Django or FastAPI\nPostgreSQL\nREST API design',
                3500, 5500, 'New York, NY', False, 'full_time',
            ),
            (
                'PR & Communications Specialist',
                'Manage public perception of Vought International and its subsidiary brands.\nYou will draft press releases, manage media relationships, and handle crisis communications.\nExperience spinning a narrative under pressure is essential.',
                'Communications or journalism degree\n5+ years in corporate PR\nMedia crisis experience',
                3200, 5000, 'New York, NY', False, 'full_time',
            ),
            (
                'Embedded Systems Engineer',
                'Develop firmware for Vought\'s defense hardware products.\nYou will write low-level C code for real-time embedded platforms.\nHardware bring-up experience is a strong advantage.',
                'C and C++\nRTOS experience\nHardware debugging skills',
                4000, 6500, 'New York, NY', False, 'full_time',
            ),
            (
                'Junior Data Analyst – Contracts',
                'Support the contracts division with data entry, reporting, and spend analysis.\nYou will work with large procurement datasets and produce weekly summaries.\nEntry-level role with room to grow into a senior analyst position.',
                'Excel and basic SQL\nAttention to detail\nDegree in business or economics',
                1800, 2800, 'New York, NY', False, 'full_time',
            ),
        ],
        'Εθνική Ασφαλιστική': [
            (
                'Fullstack Developer',
                'Develop and maintain the customer-facing portal for policy management.\nYou will work with a React frontend and a Django REST backend.\nGreek language skills required for stakeholder communication.',
                'React and Django\nPostgreSQL\nGreek language (professional level)',
                2500, 4000, 'Athens, Greece', False, 'full_time',
            ),
            (
                'Actuary',
                'Model insurance risk for life, health, and property product lines.\nYou will produce pricing recommendations and regulatory compliance reports.\nStrong statistical background and attention to precision required.',
                'Actuarial exam progress (at least 3 passed)\nR or Python for statistical modelling\nKnowledge of Greek insurance regulation',
                3500, 5500, 'Athens, Greece', False, 'full_time',
            ),
            (
                'IT Systems Administrator',
                'Maintain on-premise and hybrid cloud infrastructure for 500+ internal users.\nYou will handle provisioning, patching, backup, and helpdesk escalations.\nAfter-hours maintenance windows are expected once a month.',
                'Windows Server and Active Directory\nVMware or Hyper-V\nNetworking fundamentals',
                2200, 3500, 'Athens, Greece', False, 'full_time',
            ),
            (
                'Data Analyst – Claims',
                'Analyse claims data to identify fraud patterns and cost drivers.\nYou will build dashboards in Power BI and present findings to operations leadership.\nInsurance domain knowledge is a strong plus.',
                'SQL and Power BI\nPython for data cleaning\nAnalytical mindset',
                2000, 3200, 'Athens, Greece', False, 'full_time',
            ),
            (
                'Mobile Developer',
                'Build and maintain the Εθνική Ασφαλιστική customer mobile app on Android and iOS.\nYou will work with Flutter and integrate with existing REST APIs.\nGreek language required.',
                'Flutter and Dart\nREST API integration\nPublished apps on Play Store or App Store',
                2800, 4500, 'Athens, Greece', False, 'full_time',
            ),
            (
                'Customer Service Representative',
                'Handle inbound policy inquiries, claims reports, and renewals over phone and email.\nYou will be the first point of contact for thousands of Greek policyholders.\nEmpathy and patience are as important as product knowledge.',
                'Fluent Greek and basic English\nCRM experience\nInsurance background preferred',
                1300, 1900, 'Athens, Greece', False, 'full_time',
            ),
            (
                'IT Intern',
                'Support the IT department with helpdesk tickets, equipment setup, and documentation.\nYou will rotate across infrastructure and software teams over 3 months.\nGreat entry point into enterprise IT.',
                'Currently enrolled in IT or CS degree\nBasic networking knowledge\nFluent Greek',
                700, 1000, 'Athens, Greece', False, 'internship',
            ),
        ],
        'Microslop': [
            (
                'Senior .NET Developer',
                'Maintain and extend a legacy enterprise resource planning suite written in C#.\nYou will navigate a codebase with no tests and comments written in three languages.\nSeniority here means knowing which parts not to touch.',
                'C# and .NET Framework (not Core)\nSQL Server\nHigh tolerance for technical debt',
                3000, 5000, 'Redmond, WA', False, 'full_time',
            ),
            (
                'QA Engineer',
                'Write and execute test plans for Microslop\'s flagship productivity suite.\nYou will file detailed bug reports that will be marked as "by design" 60% of the time.\nRegression testing experience is essential.',
                'Manual and automated testing\nSelenium or similar\nPatience',
                2500, 4000, 'Redmond, WA', False, 'full_time',
            ),
            (
                'Technical Writer',
                'Write documentation for APIs and features that change without notice.\nYou will interview engineers who don\'t want to be interviewed and produce readable output.\nThe ability to explain the inexplicable is your superpower.',
                'Technical writing experience\nMarkdown and docs-as-code workflows\nAbility to read source code',
                2200, 3500, 'Remote', True, 'full_time',
            ),
            (
                'Cloud Infrastructure Engineer',
                'Migrate Microslop\'s on-premise products to Azure.\nYou will work with legacy systems that predate containerization.\nEvery win here is earned.',
                'Azure\nTerraform\nExperience with legacy lift-and-shift migrations',
                3200, 5500, 'Redmond, WA', False, 'full_time',
            ),
            (
                'Frontend Developer',
                'Build new UI features on top of an existing jQuery codebase.\nYou will incrementally migrate components to React without breaking anything.\nBrowser compatibility back to IE11 is still a requirement.',
                'React\njQuery (unfortunately)\nCSS without a framework',
                2800, 4500, 'Remote', True, 'full_time',
            ),
            (
                'Support Engineer',
                'Handle escalated technical support cases from enterprise customers.\nYou will diagnose issues across a stack you did not build and cannot fully understand.\nStrong communication and debugging skills are the job.',
                'Troubleshooting complex software environments\nSQL for log analysis\nEnterprise customer communication',
                2200, 3500, 'Redmond, WA', False, 'full_time',
            ),
            (
                'Graduate Software Engineer',
                'Join a product team and contribute to features across the stack.\nYou will be mentored by senior engineers and expected to ship within your first month.\nAmbition rewarded; complacency absorbed.',
                'CS degree or equivalent\nAny modern language\nEagerness to learn fast',
                2000, 3000, 'Redmond, WA', False, 'full_time',
            ),
        ],
        'TikTok': [
            (
                'Recommendation Algorithm Engineer',
                'Work on the core For You Page ranking model that determines what a billion users see.\nYou will run large-scale experiments and iterate on feature engineering.\nYour changes go live to hundreds of millions of users within hours.',
                'Machine learning at scale\nPython and C++\nExperience with ranking or retrieval systems',
                5000, 8500, 'Singapore', False, 'full_time',
            ),
            (
                'Backend Engineer – Live Streaming',
                'Build the infrastructure that powers TikTok Live for millions of concurrent streams.\nYou will work on latency reduction, scalability, and real-time gift processing.\nHigh availability is a hard requirement.',
                'Go or C++\nReal-time systems experience\nKnowledge of streaming protocols (WebRTC, RTMP)',
                4500, 7500, 'Singapore', False, 'full_time',
            ),
            (
                'Android Engineer',
                'Build new features for the TikTok Android app.\nYou will own features from design through rollout to 800 million Android users.\nPerformance, startup time, and smooth scrolling are your metrics.',
                'Kotlin and Android SDK\nExperience with video playback on Android\nShipped apps with 1M+ installs preferred',
                4000, 7000, 'Remote', True, 'full_time',
            ),
            (
                'Trust & Safety Engineer',
                'Build systems that detect and remove harmful content at TikTok scale.\nYou will design classifiers, write policy enforcement pipelines, and work with legal teams.\nThe work is technically challenging and genuinely important.',
                'Python and ML\nExperience with content moderation systems\nComfort working with sensitive content',
                4200, 7000, 'Singapore', False, 'full_time',
            ),
            (
                'Data Engineer – Creator Analytics',
                'Build the data pipelines behind TikTok\'s creator analytics dashboard.\nYou will work with Flink, Kafka, and Hive on datasets that never stop growing.\nCreator monetization depends on the accuracy of your pipelines.',
                'Apache Flink or Spark\nKafka\nSQL and Python',
                4000, 6500, 'Singapore', False, 'full_time',
            ),
            (
                'UX Researcher',
                'Run qualitative and quantitative research to improve TikTok\'s creator and viewer experience.\nYou will design studies, recruit participants, and present insights to product leadership.\nYour research shapes product decisions for a global audience.',
                'Mixed methods research experience\nExperience with international user populations\nStrong presentation skills',
                3500, 5500, 'Remote', True, 'full_time',
            ),
            (
                'Marketing Intern – Southeast Asia',
                'Support TikTok\'s regional marketing team with campaign execution and reporting.\nYou will coordinate with creators, track performance metrics, and produce weekly briefs.\nFast-paced environment with real ownership from week one.',
                'Currently enrolled in marketing or business degree\nFluent English, additional SEA language a plus\nPassion for short-form video',
                1000, 1500, 'Singapore', False, 'internship',
            ),
        ],
    }

    # seed jobs
    job_count = 0
    for employer in employers:
        job_list = JOBS_BY_EMPLOYER.get(employer.company_name, [])
        for (title, description, requirements, salary_min, salary_max,
             location, is_remote, contract_type) in job_list:
            JobPosting.objects.get_or_create(
                employer=employer,
                title=title,
                defaults={
                    'description':  description,
                    'requirements': requirements,
                    'salary_min':   salary_min,
                    'salary_max':   salary_max,
                    'location':     location,
                    'is_remote':    is_remote,
                    'contract_type': contract_type,
                    'is_active':    True,
                }
            )
            job_count += 1

    print(f'  {job_count} job postings created')

    #Social Posts
    AGILE_CANDIDATE_POSTS = [
        "Just wrapped up our sprint retrospective and I genuinely teared up a little. 🥹\n\nAgile didn't just change how I work — it changed who I AM.\n\nThe daily standups. The story points. The velocity charts. Pure magic.\n\n#Agile #Scrum #GrowthMindset #SoftwareEngineering",

        "Hot take: Agile is the greatest invention in human history.\n\nYes, greater than the wheel.\nYes, greater than antibiotics.\n\nThe wheel didn't have a Definition of Done. 🎯\n\n#AgileLife #Scrum #Productivity",

        "I asked my therapist why I feel so fulfilled lately.\n\nShe said it might be the new relationship.\nI said 'yes, with Agile.'\n\nShe stopped billing me after that session. I think she was moved. 💙\n\n#Agile #WorkLifeBalance #Scrum",

        "People ask me what I do on weekends.\n\nHonestly? I think about sprint planning.\nI visualize my personal Kanban board.\nI groom my own backlog.\n\nIs that weird? No. That's LIVING. 🔥\n\n#AgileEveryday #Kanban #Scrum #PersonalDevelopment",

        "Controversial opinion: story points are a form of poetry.\n\nA 3-pointer whispers 'manageable.'\nAn 8-pointer screams 'we need to talk.'\nA 13-pointer is a haiku about suffering.\n\n#StoryPoints #Agile #Engineering",

        "My morning routine:\n☀️ Wake up\n🧘 10 min mindfulness\n📋 Review my personal sprint goals\n☕ Coffee\n💻 Ship value to stakeholders\n\nAgile isn't a methodology. It's a LIFESTYLE. 🙌\n\n#AgileCoach #Scrum #GrowthMindset",

        "I once worked on a waterfall project.\n\nI don't talk about those years.\n\nAgile saved me. And it can save you too. 💪\n\n#AgileTransformation #Scrum #NeverGoingBack",

        "The retrospective format changed my relationships.\n\nWith my team: What went well / What didn't / What to improve.\nWith my family: same.\nWith my mirror every morning: same.\n\nTry it. Thank me later. ✨\n\n#Retrospective #Agile #SelfImprovement",

        "Unpopular opinion: every human interaction should have acceptance criteria.\n\nDate night? Define done.\nGrocery run? Story points.\nFamily dinner? Two-week sprint.\n\nMy partner says I need help. I say they need a product owner. 😤\n\n#Agile #AcceptanceCriteria #Scrum",

        "Just got my Scrum Master certification and I have NEVER felt more powerful.\n\nI am the impediment remover.\nI am the velocity guardian.\nI am the facilitator of ceremonies.\n\nFear me. 🧙‍♂️\n\n#ScrumMaster #Agile #Certified #NowHiring",

        "The Agile Manifesto was written in 2001.\n\nIn 2001 we also got: the iPod, Shrek, and Wikipedia.\n\nCoincidence? I don't think so. All pillars of human civilization. 🏛️\n\n#AgileManifesto #Agile #TechHistory",

        "Things Agile has taught me:\n\n✅ Embrace change\n✅ Deliver value early\n✅ Trust your team\n✅ Inspect and adapt\n✅ A sprint is not a marathon (but it feels like one at 11pm on a Thursday)\n\n#Agile #Scrum #Learnings",

        "PSA: If you're not doing daily standups you are WASTING your life.\n\n15 minutes every morning.\nWhat did you do? What will you do? Any blockers?\n\nI do this with my cat now. She has no blockers but I appreciate the transparency. 🐱\n\n#DailyStandup #Agile #Scrum",

        "I put 'Agile practitioner' on my dating profile.\n\nGot 47 matches in an hour.\n\nDeliver early. Deliver often. 💘\n\n#Agile #JustSaying #Scrum #SoftwareDevelopment",

        "Someone told me Agile is just 'common sense with meetings.'\n\nI haven't spoken to them since.\n\nSome things cannot be forgiven. 🚫\n\n#Agile #Scrum #HardTruths",
    ]

    AGILE_BUSINESS_POSTS = [
        "🚀 EXCITING NEWS from the team here at [COMPANY NAME]! 🚀\n\nWe are THRILLED to announce that we have officially completed our Agile Transformation Journey™️!\n\nWhat does this mean for YOU, our valued stakeholders?\n\n✅ Faster delivery of synergistic value\n✅ Cross-functional team empowerment paradigms\n✅ Disruption of legacy waterfall thinking\n✅ A new Jira board with 6 columns\n\nWe couldn't be more excited to continue leveraging our agile mindset to deliver world-class solutions in this rapidly evolving landscape going forward.\n\n#AgileTransformation #WeAreAgile #Innovation #Synergy #ThoughtLeadership",

        "At [COMPANY NAME], we believe that Agile is not just a process.\n\nIt's a CULTURE. 🌱\nIt's a MINDSET. 🧠\nIt's a JOURNEY. 🛤️\nIt's a FRAMEWORK. 📋\nIt's a LIFESTYLE. 💼\nIt's a VALUE STREAM. 🔄\nIt's a NORTH STAR. ⭐\n\nWe sat in a room for 3 days to define our Agile values and we are proud to share them:\n1. Be agile\n2. Think agile\n3. Do agile\n\nOur coaches charge €450/hour. Worth every penny.\n\n#AgileValues #Culture #WeAreHiring #Transformation #MindsetShift",

        "🎉 We just completed SPRINT 1! 🎉\n\nAs an organization, this is a historic moment.\n\nOur cross-functional team of 47 people, 3 Scrum Masters, 2 Agile Coaches, and 1 'Chief Agility Officer' came together to deliver:\n\n📦 1 login page\n📦 A revised color palette (still pending approval)\n📦 14 hours of retrospective notes\n\nVelocity: 4 story points.\nTarget: 80.\n\nWe are on a journey. 🚀 The destination is value. The vehicle is Agile. The fuel is passion.\n\nLike and share if Agile has changed your organization! 👇\n\n#Sprint1 #AgileOrganization #Scrum #JourneyNotDestination #Hiring",
    ]

    # Post comment pool
    AGILE_COMMENTS = [
        "This is so true!! Agile changed my career completely 🙌",
        "Couldn't agree more. Scrum is life.",
        "Sharing this with my entire team right now 🔥",
        "This is the content I come here for. Thank you for this.",
        "Preach!! The retrospective format is UNDERRATED",
        "Okay but the part about story points... I felt that 😭",
        "Daily standup with the cat sent me 💀",
        "Agile saved my last project I genuinely mean that",
        "This should be required reading for every dev team",
        "You are speaking directly to my soul right now",
        "Story points ARE poetry and I will defend this take",
        "The waterfall years... dark times. Dark times indeed.",
        "I showed this to my Scrum Master and she cried (happy tears)",
        "Certified Scrum Master here — 100% accurate 😂",
        "Can we get this framed in the office please",
    ]

    # Pick 15 random candidates for posts
    post_candidates = random.sample(candidates, min(15, len(candidates)))
    # Pick 3 employers for cringe business posts
    post_employers = random.sample(employers, min(3, len(employers)))

    # Meme images: 3 for candidates, 2 for businesses
    meme_files = [os.path.join(MEMES_DIR, f'{i}.jpg') for i in range(1, 6)]
    candidate_meme_files = meme_files[:3]   # 1.jpg, 2.jpg, 3.jpg
    business_meme_files  = meme_files[3:5]  # 4.jpg, 5.jpg

    # Pick which 3 of the 15 candidate posts get images
    meme_post_indices = random.sample(range(15), 3)

    post_count    = 0
    comment_count = 0
    like_count    = 0

    for idx, candidate_profile in enumerate(post_candidates):
        content = AGILE_CANDIDATE_POSTS[idx]
        post, created = Post.objects.get_or_create(
            user=candidate_profile.user,
            content=content,
        )

        if created:
            # Attach a meme image to 3 of the posts
            if idx in meme_post_indices:
                meme_path = candidate_meme_files[meme_post_indices.index(idx)]
                if os.path.exists(meme_path):
                    with open(meme_path, 'rb') as img:
                        pi = PostImage(post=post)
                        pi.image.save(os.path.basename(meme_path), File(img), save=True)

            # 5–6 comments from random other candidates
            commenters = random.sample(
                [c for c in candidates if c != candidate_profile],
                min(random.randint(5, 6), len(candidates) - 1)
            )
            for commenter in commenters:
                Comment.objects.get_or_create(
                    post=post,
                    user=commenter.user,
                    defaults={'content': random.choice(AGILE_COMMENTS)},
                )
                comment_count += 1

            # Likes from a random subset of candidates
            likers = random.sample(candidates, min(random.randint(8, 15), len(candidates)))
            for liker in likers:
                Like.objects.get_or_create(post=post, user=liker.user)
                like_count += 1

        post_count += 1

    # 3 business / employer posts
    for idx, employer_profile in enumerate(post_employers):
        content = AGILE_BUSINESS_POSTS[idx]
        post, created = Post.objects.get_or_create(
            user=employer_profile.user,
            content=content,
        )

        if created:
            # Attach a meme image to both business posts (indices 0 and 1)
            if idx < 2:
                meme_path = business_meme_files[idx]
                if os.path.exists(meme_path):
                    with open(meme_path, 'rb') as img:
                        pi = PostImage(post=post)
                        pi.image.save(os.path.basename(meme_path), File(img), save=True)

            # 5–6 comments from random candidates
            commenters = random.sample(candidates, min(random.randint(5, 6), len(candidates)))
            for commenter in commenters:
                Comment.objects.get_or_create(
                    post=post,
                    user=commenter.user,
                    defaults={'content': random.choice(AGILE_COMMENTS)},
                )
                comment_count += 1

            # Likes from a random subset of candidates
            likers = random.sample(candidates, min(random.randint(6, 12), len(candidates)))
            for liker in likers:
                Like.objects.get_or_create(post=post, user=liker.user)
                like_count += 1

        post_count += 1

    print(f'  {post_count} social posts created')
    print(f'  {comment_count} comments created')
    print(f'  {like_count} likes created')
    print('Done — all good!')


if __name__ == '__main__':
    seed()
