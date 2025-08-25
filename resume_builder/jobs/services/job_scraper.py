# services/job_scraper.py

import requests
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urlparse, urljoin
from typing import Dict, List, Optional, Tuple, Set
import time
from django.utils import timezone
from ..models import JobPosting

class JobDescriptionScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Common skills database for parsing
        self.skill_patterns = self._load_skill_patterns()
        
        # ATS platform configurations
        self.ats_configs = {
            'greenhouse': {
                'job_selectors': ['.job-post-content', '.job-post', '.posting-content'],
                'title_selectors': ['.job-post-title', '.posting-headline h2', 'h1'],
                'company_selectors': ['.company-name', '.posting-company h2'],
                'location_selectors': ['.location', '.posting-categories .location'],
                'description_selectors': ['.job-post-description', '.posting-description']
            },
            'lever': {
                'job_selectors': ['.posting-content', '.posting'],
                'title_selectors': ['.posting-headline h2', 'h1'],
                'company_selectors': ['.posting-company h2', '.company-name'],
                'location_selectors': ['.posting-categories .location', '.location'],
                'description_selectors': ['.posting-description', '.content']
            },
            'workday': {
                'job_selectors': ['.jobdescription', '.job-description'],
                'title_selectors': ['h1[data-automation-id="jobPostingHeader"]', 'h1'],
                'company_selectors': ['.company-name', 'h2'],
                'location_selectors': ['.jobdescription .location', '.location'],
                'description_selectors': ['.jobdescription .content', '.job-description']
            },
            'generic': {
                'job_selectors': ['.job-post', '.job-description', '.posting', 'main', 'article'],
                'title_selectors': ['h1', 'h2', '.job-title', '.title'],
                'company_selectors': ['.company', '.company-name', 'h2'],
                'location_selectors': ['.location', '.job-location'],
                'description_selectors': ['.description', '.content', '.job-description']
            }
        }

    def scrape_job_from_url(self, url: str, user=None) -> JobPosting:
        """Main method to scrape a job from URL and create JobPosting"""
        try:
            # Step 1: Fetch the page
            html_content = self._fetch_page(url)
            
            # Step 2: Identify ATS platform
            ats_platform = self._identify_ats_platform(url, html_content)
            
            # Step 3: Parse job content
            job_data = self._parse_job_content(html_content, ats_platform)
            job_data['original_url'] = url
            job_data['ats_platform'] = ats_platform
            job_data['scraped_at'] = timezone.now().isoformat()
            
            # Step 4: Parse job description for skills and requirements
            parsed_requirements = self._parse_job_requirements(job_data.get('description_text', ''))
            
            # Step 5: Build final JSON structure
            json_data = {
                'scraped_content': {
                    'full_description': job_data.get('description_text', ''),
                    'description_html': job_data.get('description_html', ''),
                    'company_info': job_data.get('company_description', ''),
                    'benefits': job_data.get('benefits', ''),
                    'original_url': url,
                    'ats_platform': ats_platform
                },
                'parsed_requirements': parsed_requirements,
                'matching_opportunities': self._identify_matching_opportunities(parsed_requirements),
                'scraping_metadata': {
                    'success': True,
                    'scraped_at': timezone.now().isoformat(),
                    'scraper_version': '1.0.0'
                }
            }
            
            # Step 6: Create JobPosting record
            job_posting = JobPosting.objects.create(
                url=url,
                company_name=job_data.get('company_name', 'Unknown Company'),
                job_title=job_data.get('job_title', 'Unknown Position'),
                location=job_data.get('location', ''),
                remote_ok=self._is_remote_job(job_data.get('description_text', '')),
                raw_json=json_data,
                added_by=user,
                scraping_success=True
            )
            
            return job_posting
            
        except Exception as e:
            # Create failed record for debugging
            job_posting = JobPosting.objects.create(
                url=url,
                company_name='Scraping Failed',
                job_title='Could Not Parse',
                scraping_success=False,
                scraping_error=str(e),
                raw_json={
                    'scraping_metadata': {
                        'success': False,
                        'error': str(e),
                        'scraped_at': timezone.now().isoformat()
                    }
                },
                added_by=user
            )
            raise Exception(f"Failed to scrape job: {str(e)}")

    def _fetch_page(self, url: str) -> str:
        """Fetch HTML content from URL"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch page: {str(e)}")

    def _identify_ats_platform(self, url: str, html_content: str) -> str:
        """Identify which ATS platform is being used"""
        url_lower = url.lower()
        html_lower = html_content.lower()
        
        if 'greenhouse.io' in url_lower or 'greenhouse' in html_lower:
            return 'greenhouse'
        elif 'jobs.lever.co' in url_lower or 'lever' in html_lower:
            return 'lever'
        elif 'myworkdayjobs.com' in url_lower or 'workday' in html_lower:
            return 'workday'
        else:
            return 'generic'

    def _parse_job_content(self, html_content: str, ats_platform: str) -> Dict:
        """Parse job content using ATS-specific selectors"""
        soup = BeautifulSoup(html_content, 'html.parser')
        config = self.ats_configs.get(ats_platform, self.ats_configs['generic'])
        
        job_data = {}
        
        # Extract job title
        job_data['job_title'] = self._extract_with_selectors(soup, config['title_selectors'])
        
        # Extract company name with enhanced methods
        job_data['company_name'] = self._extract_company_name(soup, config)
        
        # Extract location with better filtering
        job_data['location'] = self._extract_location_cleaned(soup, config)
        
        # Extract job description
        description_element = self._find_with_selectors(soup, config['description_selectors'])
        if description_element:
            job_data['description_html'] = str(description_element)
            job_data['description_text'] = description_element.get_text(strip=True, separator='\n')
        
        # Try to find additional sections
        job_data['benefits'] = self._extract_section(soup, ['benefits', 'perks', 'what we offer'])
        job_data['company_description'] = self._extract_section(soup, ['about us', 'about the company', 'company'])
        
        return job_data

    def _extract_company_name(self, soup: BeautifulSoup, config: Dict) -> str:
        """Enhanced company name extraction with fallback methods"""
        # Try standard selectors first
        company_name = self._extract_with_selectors(soup, config['company_selectors'])
        
        # Check if we got placeholder text
        if self._is_placeholder_text(company_name):
            company_name = ""
        
        # Fallback methods if standard extraction failed or returned placeholder
        if not company_name:
            # Try meta tags
            company_name = self._extract_from_meta_tags(soup)
            
            # Try structured data (JSON-LD)
            if not company_name:
                company_name = self._extract_from_structured_data(soup)
            
            # Try URL analysis
            if not company_name:
                company_name = self._extract_company_from_url(soup)
            
            # Try page title
            if not company_name:
                company_name = self._extract_company_from_title(soup)
        
        return company_name or "Unknown Company"

    def _extract_location_cleaned(self, soup: BeautifulSoup, config: Dict) -> str:
        """Extract location with placeholder filtering"""
        location = self._extract_with_selectors(soup, config['location_selectors'])
        
        # Check if we got placeholder text and clean it
        if self._is_placeholder_text(location):
            location = ""
        
        # Clean up location text
        if location:
            # Remove common placeholder patterns
            location = re.sub(r'%[A-Z_]+%', '', location)
            # Clean up extra spaces and punctuation
            location = re.sub(r'\s+', ' ', location).strip()
            location = location.strip('•').strip('-').strip()
        
        return location

    def _is_placeholder_text(self, text: str) -> bool:
        """Check if text contains placeholder patterns"""
        if not text:
            return True
        
        placeholder_patterns = [
            r'%[A-Z_]+%',  # %HEADER_COMPANY_WEBSITE%, %LABEL_POSITION_TYPE_REMOTE_ANY%
            r'\{\{.*?\}\}',  # {{company_name}}
            r'\[.*?\]',  # [COMPANY]
            r'COMPANY_NAME',
            r'PLACEHOLDER',
            r'TBD',
            r'TO_BE_DETERMINED'
        ]
        
        for pattern in placeholder_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False

    def _extract_from_meta_tags(self, soup: BeautifulSoup) -> str:
        """Extract company name from meta tags"""
        # Try Open Graph tags
        og_site_name = soup.find('meta', property='og:site_name')
        if og_site_name and og_site_name.get('content'):
            return og_site_name['content']
        
        # Try Twitter card
        twitter_site = soup.find('meta', attrs={'name': 'twitter:site'})
        if twitter_site and twitter_site.get('content'):
            return twitter_site['content'].lstrip('@')
        
        # Try application-name
        app_name = soup.find('meta', attrs={'name': 'application-name'})
        if app_name and app_name.get('content'):
            return app_name['content']
        
        return ""

    def _extract_from_structured_data(self, soup: BeautifulSoup) -> str:
        """Extract company name from JSON-LD structured data"""
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Look for Organization or JobPosting schema
                    if data.get('@type') == 'Organization' and data.get('name'):
                        return data['name']
                    elif data.get('@type') == 'JobPosting':
                        hiring_org = data.get('hiringOrganization', {})
                        if hiring_org.get('name'):
                            return hiring_org['name']
        except (json.JSONDecodeError, KeyError):
            pass
        return ""

    def _extract_company_from_url(self, soup: BeautifulSoup) -> str:
        """Extract company name from URL patterns"""
        # Get the canonical URL or current URL
        canonical = soup.find('link', rel='canonical')
        if canonical and canonical.get('href'):
            url = canonical['href']
        else:
            url = soup.find('meta', property='og:url')
            if url and url.get('content'):
                url = url['content']
            else:
                return ""
        
        # Extract domain and try to infer company name
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove common subdomains
        domain = re.sub(r'^(www\.|jobs\.|careers\.|apply\.)', '', domain)
        
        # Remove TLD and convert to title case
        company = domain.split('.')[0].replace('-', ' ').replace('_', ' ').title()
        
        return company if len(company) > 2 else ""

    def _extract_company_from_title(self, soup: BeautifulSoup) -> str:
        """Extract company name from page title"""
        title_tag = soup.find('title')
        if not title_tag:
            return ""
        
        title = title_tag.get_text()
        
        # Common patterns in job posting titles
        patterns = [
            r'(.+?)\s*-\s*Careers?',
            r'(.+?)\s*-\s*Jobs?',
            r'(.+?)\s*\|\s*Careers?',
            r'(.+?)\s*\|\s*Jobs?',
            r'Jobs?\s*at\s*(.+?)(?:\s*-|\s*\||$)',
            r'Careers?\s*at\s*(.+?)(?:\s*-|\s*\||$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                if not self._is_placeholder_text(company) and len(company) > 2:
                    return company
        
        return ""

    def _extract_with_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """Try multiple selectors and return first match"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
        return ''

    def _find_with_selectors(self, soup: BeautifulSoup, selectors: List[str]):
        """Find element using multiple selectors"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element
        return None

    def _extract_section(self, soup: BeautifulSoup, keywords: List[str]) -> str:
        """Extract text from sections containing specific keywords"""
        for keyword in keywords:
            # Look for headings containing the keyword
            heading = soup.find(['h1', 'h2', 'h3', 'h4'], string=re.compile(keyword, re.I))
            if heading:
                # Get the next sibling content
                content = []
                for sibling in heading.find_next_siblings():
                    if sibling.name in ['h1', 'h2', 'h3', 'h4']:
                        break
                    content.append(sibling.get_text(strip=True))
                return '\n'.join(content)
        return ''

    def _parse_job_requirements(self, job_text: str) -> Dict:
        """Enhanced parsing of job description to extract requirements and skills"""
        text_lower = job_text.lower()
        
        # Extract skills using multiple methods
        required_skills = set()
        preferred_skills = set()
        
        # Method 1: Extract from parenthetical examples
        parenthetical_skills = self._extract_parenthetical_skills(job_text)
        
        # Method 2: Extract from bullet points and structured lists  
        bullet_skills = self._extract_skills_from_bullets(job_text)
        
        # Method 3: Traditional keyword matching
        keyword_skills = self._extract_keyword_skills(text_lower)
        
        # Method 4: Extract skills from experience requirements
        experience_skills = self._extract_skills_from_experience_context(job_text)
        
        # Combine all extracted skills
        all_found_skills = parenthetical_skills | bullet_skills | keyword_skills | experience_skills
        
        # Categorize as required vs preferred based on context
        for skill in all_found_skills:
            if self._is_skill_required(job_text, skill):
                required_skills.add(skill)
            else:
                preferred_skills.add(skill)
        
        # Extract experience requirements
        experience_years = self._extract_experience_years(job_text)
        
        # Extract education requirements
        education_req = self._extract_education_requirements(job_text)
        
        # Extract specific requirements (bullet points, key phrases)
        specific_requirements = self._extract_specific_requirements(job_text)
        
        return {
            'required_skills': list(required_skills),
            'preferred_skills': list(preferred_skills),
            'experience_years': experience_years,
            'education': education_req,
            'specific_requirements': specific_requirements
        }

    def _extract_parenthetical_skills(self, job_text: str) -> set:
        """Extract skills mentioned in parentheses like '(e.g., Snowflake, Azure, AWS)'"""
        skills = set()
        
        # Pattern for parenthetical examples
        patterns = [
            r'\(e\.g\.?,\s*([^)]+)\)',
            r'\(such as\s*([^)]+)\)',
            r'\(including\s*([^)]+)\)',
            r'\(like\s*([^)]+)\)',
            r'\(i\.e\.?,\s*([^)]+)\)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, job_text, re.IGNORECASE)
            for match in matches:
                # Split the content by commas and clean up
                skill_list = match.group(1).split(',')
                for skill in skill_list:
                    cleaned_skill = self._clean_skill_text(skill)
                    if self._is_valid_skill(cleaned_skill):
                        skills.add(cleaned_skill)
        
        return skills

    def _extract_skills_from_bullets(self, job_text: str) -> set:
        """Extract skills from bullet points and structured requirements"""
        skills = set()
        
        # Find bullet points
        bullet_patterns = [
            r'[•\-\*]\s*(.+?)(?=\n[•\-\*]|\n\n|$)',
            r'^\s*\d+[\.\)]\s*(.+?)(?=\n\s*\d+[\.\)]|\n\n|$)',
        ]
        
        bullets = []
        for pattern in bullet_patterns:
            bullets.extend(re.findall(pattern, job_text, re.MULTILINE | re.DOTALL))
        
        # Extract skills from each bullet point
        for bullet in bullets:
            bullet = bullet.strip()
            if len(bullet) < 10:  # Skip very short bullets
                continue
            
            # Look for technology mentions
            tech_skills = self._extract_tech_skills_from_text(bullet)
            skills.update(tech_skills)
            
            # Look for platform/tool mentions
            platform_skills = self._extract_platform_skills(bullet)
            skills.update(platform_skills)
            
            # Look for methodology/framework skills
            method_skills = self._extract_methodology_skills(bullet)
            skills.update(method_skills)
        
        return skills

    def _extract_keyword_skills(self, text_lower: str) -> set:
        """Traditional keyword-based skill extraction with enhanced skill database"""
        skills = set()
        enhanced_skills = self._get_enhanced_skill_database()
        
        for category, skill_list in enhanced_skills.items():
            for skill in skill_list:
                # Use word boundaries to avoid false matches
                pattern = r'\b' + re.escape(skill.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    skills.add(skill)
        
        return skills

    def _extract_skills_from_experience_context(self, job_text: str) -> set:
        """Extract skills from experience requirement contexts"""
        skills = set()
        
        # Look for "experience with/in" patterns
        experience_patterns = [
            r'experience (?:with|in|using|developing)\s+([^.\n]+)',
            r'expertise (?:with|in|using)\s+([^.\n]+)',
            r'proficiency (?:with|in|using)\s+([^.\n]+)',
            r'knowledge of\s+([^.\n]+)',
            r'skilled in\s+([^.\n]+)',
            r'background in\s+([^.\n]+)',
        ]
        
        for pattern in experience_patterns:
            matches = re.finditer(pattern, job_text, re.IGNORECASE)
            for match in matches:
                skill_text = match.group(1).strip()
                # Extract individual skills from the text
                extracted = self._parse_skill_list(skill_text)
                skills.update(extracted)
        
        return skills

    def _parse_skill_list(self, skill_text: str) -> set:
        """Parse a text string that contains multiple skills"""
        skills = set()
        
        # Split by common delimiters
        delimiters = [',', ';', '&', ' and ', ' or ', '/']
        skill_list = [skill_text]
        
        for delimiter in delimiters:
            new_list = []
            for item in skill_list:
                new_list.extend([s.strip() for s in item.split(delimiter)])
            skill_list = new_list
        
        # Clean and validate each skill
        for skill in skill_list:
            cleaned = self._clean_skill_text(skill)
            if self._is_valid_skill(cleaned):
                skills.add(cleaned)
        
        return skills

    def _clean_skill_text(self, skill: str) -> str:
        """Clean and normalize skill text"""
        # Remove common prefixes/suffixes
        skill = re.sub(r'^(strong\s+|solid\s+|deep\s+|extensive\s+)', '', skill, flags=re.IGNORECASE)
        skill = re.sub(r'\s+(experience|knowledge|skills?|expertise|proficiency)', '', skill, flags=re.IGNORECASE)

    def _is_skill_required(self, job_text: str, skill: str) -> bool:
        """Determine if a skill is required or preferred based on context"""
        # Get context around the skill mention
        skill_pattern = re.compile(r'.{0,100}\b' + re.escape(skill) + r'\b.{0,100}', re.IGNORECASE)
        matches = skill_pattern.findall(job_text)
        
        for match in matches:
            match_lower = match.lower()
            if any(word in match_lower for word in ['required', 'must', 'essential', 'mandatory']):
                return True
            if any(word in match_lower for word in ['preferred', 'nice', 'bonus', 'plus']):
                return False
        
        # Default to required if context is unclear
        return True

    def _extract_experience_years(self, job_text: str) -> str:
        """Extract years of experience requirements"""
        patterns = [
            r'(\d+)\+?\s*(?:to\s*\d+\s*)?years?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*(?:to\s*\d+\s*)?yrs?\s*(?:of\s*)?experience',
            r'minimum\s*(?:of\s*)?(\d+)\s*years?',
            r'at\s*least\s*(\d+)\s*years?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, job_text, re.IGNORECASE)
            if match:
                return f"{match.group(1)}+ years"
        
        return ''

    def _extract_education_requirements(self, job_text: str) -> str:
        """Extract education requirements"""
        education_patterns = [
            r"bachelor['\']?s?\s*degree",
            r"master['\']?s?\s*degree", 
            r"phd|doctorate",
            r"associate['\']?s?\s*degree",
            r"high\s*school|diploma"
        ]
        
        for pattern in education_patterns:
            if re.search(pattern, job_text, re.IGNORECASE):
                return re.search(pattern, job_text, re.IGNORECASE).group(0)
        
        return ''

    def _extract_specific_requirements(self, job_text: str) -> List[str]:
        """Extract specific bullet-point requirements"""
        requirements = []
        
        # Look for bullet points or numbered lists
        bullet_patterns = [
            r'[•\-\*]\s*(.+?)(?=\n|$)',
            r'\d+\.\s*(.+?)(?=\n|$)',
            r'(?:^|\n)\s*[•\-\*]\s*(.+?)(?=\n|$)'
        ]
        
        for pattern in bullet_patterns:
            matches = re.findall(pattern, job_text, re.MULTILINE)
            for match in matches:
                clean_req = match.strip()
                if len(clean_req) > 10 and len(clean_req) < 200:  # Reasonable length
                    requirements.append(clean_req)
        
        return requirements[:10]  # Limit to top 10 requirements

    def _identify_matching_opportunities(self, parsed_requirements: Dict) -> Dict:
        """Identify key areas for resume/story matching"""
        opportunities = {}
        
        # Identify key technology focus
        tech_skills = [s for s in parsed_requirements.get('required_skills', []) 
                      if s.lower() in self.skill_patterns.get('technical', [])]
        opportunities['key_technologies'] = tech_skills[:5]
        
        # Check for leadership indicators
        leadership_keywords = ['lead', 'manage', 'mentor', 'team', 'direct', 'supervise']
        has_leadership = any(keyword in ' '.join(parsed_requirements.get('specific_requirements', [])).lower() 
                           for keyword in leadership_keywords)
        opportunities['leadership_emphasis'] = has_leadership
        
        # Check for scale/performance requirements
        scale_keywords = ['scale', 'performance', 'million', 'billion', 'high traffic', 'optimization']
        has_scale = any(keyword in ' '.join(parsed_requirements.get('specific_requirements', [])).lower() 
                       for keyword in scale_keywords)
        opportunities['scale_requirements'] = has_scale
        
        return opportunities

    def _is_remote_job(self, job_text: str) -> bool:
        """Check if job allows remote work"""
        remote_keywords = ['remote', 'work from home', 'telecommute', 'distributed', 'anywhere']
        return any(keyword in job_text.lower() for keyword in remote_keywords)

    def _load_skill_patterns(self) -> Dict[str, List[str]]:
        """Load basic skill patterns (now using enhanced database in extraction)"""
        # This is now mainly for backward compatibility
        # The real skill extraction uses _get_enhanced_skill_database()
        return {
            'technical': ['python', 'javascript', 'aws', 'azure', 'docker'],
            'soft_skills': ['communication', 'leadership', 'teamwork'],
            'all_skills': ['python', 'javascript', 'aws', 'azure', 'docker', 'communication', 'leadership']
        }

    def _init_skill_patterns():
        scraper = JobDescriptionScraper()
        
        # Merge technical and soft skills into all_skills
        scraper.skill_patterns['all_skills'] = (
            scraper.skill_patterns['technical'] + scraper.skill_patterns['soft_skills']
        )
        
        cleaned_skills = []
        
        for skill in scraper.skill_patterns['all_skills']:
            # Remove parenthetical clarifications but keep the main skill
            skill = re.sub(r'\s*\([^)]+\)', '', skill)
            
            # Clean up whitespace
            skill = re.sub(r'\s+', ' ', skill).strip()
            
            # Capitalize properly
            if skill.isupper() or skill.islower():
                # Handle acronyms vs regular words
                if len(skill) <= 4 and skill.isupper():
                    cleaned_skills.append(skill)  # Keep acronyms uppercase
                else:
                    cleaned_skills.append(skill.title())
            else:
                cleaned_skills.append(skill)
        
        # Replace all_skills with cleaned version
        scraper.skill_patterns['all_skills'] = cleaned_skills
        
        return scraper


    def _is_valid_skill(self, skill: str) -> bool:
        """Check if extracted text is a valid skill"""
        if not skill or len(skill) < 2:
            return False
        
        # Skip common non-skills
        non_skills = {
            'experience', 'knowledge', 'skills', 'ability', 'capability',
            'strong', 'solid', 'deep', 'extensive', 'proven', 'excellent',
            'years', 'year', 'minimum', 'preferred', 'required', 'must',
            'and', 'or', 'with', 'in', 'of', 'the', 'a', 'an', 'to'
        }
        
        if skill.lower() in non_skills:
            return False
        
        # Skip very long skills (likely sentences)
        if len(skill) > 50:
            return False
        
        # Skip skills that are mostly punctuation
        if len(re.sub(r'[^\w\s]', '', skill)) < len(skill) * 0.7:
            return False
        
        return True

    def _extract_tech_skills_from_text(self, text: str) -> set:
        """Extract technical skills from text using patterns"""
        skills = set()
        text_lower = text.lower()
        
        # Technology keywords with context
        tech_patterns = [
            r'\b(python|java|javascript|typescript|c\+\+|c#|ruby|php|go|rust|scala|kotlin)\b',
            r'\b(react|angular|vue|django|flask|spring|express|laravel|rails)\b',
            r'\b(aws|azure|gcp|google cloud|amazon web services|microsoft azure)\b',
            r'\b(docker|kubernetes|jenkins|terraform|ansible|puppet)\b',
            r'\b(mysql|postgresql|mongodb|redis|elasticsearch|cassandra)\b',
            r'\b(git|github|gitlab|bitbucket|svn)\b',
            r'\b(linux|unix|windows|macos)\b',
            r'\b(spark|hadoop|kafka|airflow|dbt)\b',
            r'\b(snowflake|databricks|tableau|power bi|looker)\b',
        ]
        
        for pattern in tech_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                skill = match.group(1)
                # Normalize common variations
                if skill in ['gcp', 'google cloud']:
                    skills.add('Google Cloud Platform')
                elif skill in ['aws', 'amazon web services']:
                    skills.add('AWS')
                elif skill in ['azure', 'microsoft azure']:
                    skills.add('Azure')
                else:
                    skills.add(skill.title())
        
        return skills

    def _extract_platform_skills(self, text: str) -> set:
        """Extract platform and tool skills"""
        skills = set()
        text_lower = text.lower()
        
        platform_keywords = [
            'salesforce', 'servicenow', 'workday', 'oracle', 'sap',
            'jira', 'confluence', 'slack', 'teams', 'zoom',
            'figma', 'sketch', 'adobe', 'photoshop', 'illustrator'
        ]
        
        for keyword in platform_keywords:
            if keyword in text_lower:
                skills.add(keyword.title())
        
        return skills

    def _extract_methodology_skills(self, text: str) -> set:
        """Extract methodology and process skills"""
        skills = set()
        text_lower = text.lower()
        
        methodology_keywords = [
            'agile', 'scrum', 'kanban', 'waterfall', 'devops', 'ci/cd',
            'machine learning', 'deep learning', 'data science', 'analytics',
            'microservices', 'api development', 'rest api', 'graphql',
            'test driven development', 'pair programming', 'code review'
        ]
        
        for keyword in methodology_keywords:
            if keyword in text_lower:
                if keyword == 'ci/cd':
                    skills.add('CI/CD')
                elif keyword == 'rest api':
                    skills.add('REST API')
                elif keyword == 'graphql':
                    skills.add('GraphQL')
                else:
                    skills.add(keyword.title())
        
        return skills

    def _get_enhanced_skill_database(self) -> Dict[str, List[str]]:
        """Enhanced skill database with more comprehensive coverage"""
        return {
            'programming_languages': [
                'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Ruby', 
                'PHP', 'Go', 'Rust', 'Scala', 'Kotlin', 'Swift', 'R', 'MATLAB',
                'SQL', 'NoSQL', 'HTML', 'CSS', 'Bash', 'PowerShell'
            ],
            'frameworks_libraries': [
                'React', 'Angular', 'Vue.js', 'Django', 'Flask', 'FastAPI', 
                'Spring', 'Express.js', 'Laravel', 'Rails', 'ASP.NET',
                'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy'
            ],
            'cloud_platforms': [
                'AWS', 'Azure', 'Google Cloud Platform', 'Snowflake', 'Databricks',
                'Amazon S3', 'EC2', 'Lambda', 'RDS', 'CloudFormation'
            ],
            'databases': [
                'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch',
                'Cassandra', 'DynamoDB', 'Oracle', 'SQL Server', 'SQLite'
            ],
            'devops_tools': [
                'Docker', 'Kubernetes', 'Jenkins', 'GitLab CI', 'GitHub Actions',
                'Terraform', 'Ansible', 'Puppet', 'Chef', 'Helm'
            ],
            'data_tools': [
                'Apache Spark', 'Hadoop', 'Kafka', 'Airflow', 'dbt',
                'Tableau', 'Power BI', 'Looker', 'Grafana', 'Prometheus'
            ],
            'methodologies': [
                'Agile', 'Scrum', 'Kanban', 'DevOps', 'CI/CD', 'TDD',
                'Machine Learning', 'Data Science', 'Microservices'
            ],
            'soft_skills': [
                'Leadership', 'Communication', 'Project Management', 'Team Management',
                'Strategic Planning', 'Problem Solving', 'Critical Thinking',
                'Stakeholder Management', 'Cross-functional Collaboration'
            ]
        }

    def _is_remote_job(self, job_text: str) -> bool:
        """Enhanced remote work detection"""
        text_lower = job_text.lower()
        
        # Skip if we detect placeholder text
        if '%' in job_text and 'remote' in job_text:
            # Look for actual remote indicators, not placeholders
            remote_patterns = [
                r'remote.{0,20}work',
                r'work.{0,20}from.{0,10}home',
                r'distributed.{0,10}team',
                r'location.{0,10}independent',
                r'anywhere',
                r'100% remote',
                r'fully remote',
                r'remote first',
                r'remote friendly'
            ]
            
            for pattern in remote_patterns:
                if re.search(pattern, text_lower) and not re.search(r'%[A-Z_]*REMOTE[A-Z_]*%', job_text):
                    return True
                    
            return False
        
        # Standard remote detection
        remote_keywords = [
            'remote', 'work from home', 'telecommute', 'distributed',
            'anywhere', '100% remote', 'fully remote', 'remote first'
        ]
        return any(keyword in text_lower for keyword in remote_keywords)

    def _is_skill_required(self, job_text: str, skill: str) -> bool:
        """Determine if a skill is required or preferred based on context"""
        # Get context around the skill mention
        skill_pattern = re.compile(r'.{0,100}\b' + re.escape(skill) + r'\b.{0,100}', re.IGNORECASE)
        matches = skill_pattern.findall(job_text)
        
        for match in matches:
            match_lower = match.lower()
            if any(word in match_lower for word in ['required', 'must', 'essential', 'mandatory']):
                return True
            if any(word in match_lower for word in ['preferred', 'nice', 'bonus', 'plus']):
                return False
        
        # Default to required if context is unclear
        return True

    def _extract_experience_years(self, job_text: str) -> str:
        """Extract years of experience requirements"""
        patterns = [
            r'(\d+)\+?\s*(?:to\s*\d+\s*)?years?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*(?:to\s*\d+\s*)?yrs?\s*(?:of\s*)?experience',
            r'minimum\s*(?:of\s*)?(\d+)\s*years?',
            r'at\s*least\s*(\d+)\s*years?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, job_text, re.IGNORECASE)
            if match:
                return f"{match.group(1)}+ years"
        
        return ''

    def _extract_education_requirements(self, job_text: str) -> str:
        """Extract education requirements"""
        education_patterns = [
            r"bachelor['\']?s?\s*degree",
            r"master['\']?s?\s*degree", 
            r"phd|doctorate",
            r"associate['\']?s?\s*degree",
            r"high\s*school|diploma"
        ]
        
        for pattern in education_patterns:
            if re.search(pattern, job_text, re.IGNORECASE):
                return re.search(pattern, job_text, re.IGNORECASE).group(0)
        
        return ''

    def _extract_specific_requirements(self, job_text: str) -> List[str]:
        """Extract specific bullet-point requirements"""
        requirements = []
        
        # Look for bullet points or numbered lists
        bullet_patterns = [
            r'[•\-\*]\s*(.+?)(?=\n|$)',
            r'\d+\.\s*(.+?)(?=\n|$)',
            r'(?:^|\n)\s*[•\-\*]\s*(.+?)(?=\n|$)'
        ]
        
        for pattern in bullet_patterns:
            matches = re.findall(pattern, job_text, re.MULTILINE)
            for match in matches:
                clean_req = match.strip()
                if len(clean_req) > 10 and len(clean_req) < 200:  # Reasonable length
                    requirements.append(clean_req)
        
        return requirements[:10]  # Limit to top 10 requirements

    def _identify_matching_opportunities(self, parsed_requirements: Dict) -> Dict:
        """Identify key areas for resume/story matching"""
        opportunities = {}
        
        # Identify key technology focus
        tech_skills = [s for s in parsed_requirements.get('required_skills', []) 
                      if s.lower() in self.skill_patterns.get('technical', [])]
        opportunities['key_technologies'] = tech_skills[:5]
        
        # Check for leadership indicators
        leadership_keywords = ['lead', 'manage', 'mentor', 'team', 'direct', 'supervise']
        has_leadership = any(keyword in ' '.join(parsed_requirements.get('specific_requirements', [])).lower() 
                           for keyword in leadership_keywords)
        opportunities['leadership_emphasis'] = has_leadership
        
        # Check for scale/performance requirements
        scale_keywords = ['scale', 'performance', 'million', 'billion', 'high traffic', 'optimization']
        has_scale = any(keyword in ' '.join(parsed_requirements.get('specific_requirements', [])).lower() 
                       for keyword in scale_keywords)
        opportunities['scale_requirements'] = has_scale
        
        return opportunities

    def _is_remote_job(self, job_text: str) -> bool:
        """Check if job allows remote work"""
        remote_keywords = ['remote', 'work from home', 'telecommute', 'distributed', 'anywhere']
        return any(keyword in job_text.lower() for keyword in remote_keywords)

    def _load_skill_patterns(self) -> Dict[str, List[str]]:
        """Load common skills for pattern matching"""
        return {
            'technical': [
                'python', 'javascript', 'java', 'react', 'angular', 'vue', 'django', 'flask',
                'node.js', 'express', 'spring', 'mysql', 'postgresql', 'mongodb', 'redis',
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git', 'linux'
            ],
            'soft_skills': [
                'communication', 'leadership', 'teamwork', 'problem solving', 'analytical',
                'creative', 'detail oriented', 'time management', 'project management'
            ],
            'all_skills': []  # Will be populated by combining the above
        }

# Initialize all_skills list
def _init_skill_patterns():
    scraper = JobDescriptionScraper()
    scraper.skill_patterns['all_skills'] = (
        scraper.skill_patterns['technical'] + 
        scraper.skill_patterns['soft_skills']
    )