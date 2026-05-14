import requests
from bs4 import BeautifulSoup
import time
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class HHParser:
    BASE_URL = "https://hh.kz/search/vacancy"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://hh.kz/",
    }

    def search_jobs(self, query: str, city: str = "Астана", pages: int = 2) -> list[dict]:
        """
        Search vacancies on hh.kz by query and city.
        Returns list of vacancy dicts.
        """
        all_jobs = []
        
        # Area code for Astana (Nur-Sultan) on hh.kz
        area_map = {
            "Астана": "160",
            "Алматы": "159",
            "Шымкент": "202",
        }
        area_id = area_map.get(city, "160")
        
        for page in range(pages):
            params = {
                "text": query,
                "area": area_id,
                "page": page,
                "per_page": 20,
                "search_field": "name,description",
                "order_by": "relevance",
            }
            
            try:
                response = requests.get(
                    self.BASE_URL,
                    params=params,
                    headers=self.HEADERS,
                    timeout=15
                )
                response.raise_for_status()
                
                jobs = self._parse_page(response.text)
                all_jobs.extend(jobs)
                
                if len(jobs) < 5:
                    break
                
                time.sleep(1)  # Respectful delay
                
            except requests.RequestException as e:
                logger.error(f"Request error on page {page}: {e}")
                break
            except Exception as e:
                logger.error(f"Parse error on page {page}: {e}")
                break
        
        return all_jobs

    def _parse_page(self, html: str) -> list[dict]:
        """Parse vacancy cards from HTML page."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        
        # hh.kz vacancy card selectors
        vacancy_cards = soup.find_all("div", {"data-qa": "vacancy-serp__vacancy"})
        
        if not vacancy_cards:
            # Try alternative selectors
            vacancy_cards = soup.find_all("div", class_=re.compile(r"vacancy-card"))
        
        if not vacancy_cards:
            # Generic fallback
            vacancy_cards = soup.find_all("article", class_=re.compile(r"vacancy"))
        
        for card in vacancy_cards:
            try:
                job = self._parse_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"Card parse error: {e}")
                continue
        
        return jobs

    def _parse_card(self, card) -> Optional[dict]:
        """Parse a single vacancy card."""
        
        # Title and URL
        title_el = (
            card.find("a", {"data-qa": "serp-item__title"}) or
            card.find("a", class_=re.compile(r"title|name")) or
            card.find("h3") or
            card.find("h2")
        )
        
        if not title_el:
            return None
        
        title = title_el.get_text(strip=True)
        url = title_el.get("href", "")
        if url and not url.startswith("http"):
            url = "https://hh.kz" + url
        
        # Extract vacancy ID from URL
        job_id = ""
        match = re.search(r"/vacancy/(\d+)", url)
        if match:
            job_id = match.group(1)
        else:
            job_id = str(hash(title + url))[:12]
        
        # Company name
        company_el = (
            card.find("a", {"data-qa": "vacancy-serp__vacancy-employer"}) or
            card.find("span", {"data-qa": "vacancy-serp__vacancy-employer"}) or
            card.find("div", class_=re.compile(r"company|employer")) or
            card.find("a", class_=re.compile(r"company|employer"))
        )
        company = company_el.get_text(strip=True) if company_el else "Компания не указана"
        
        # Salary
        salary_el = (
            card.find("span", {"data-qa": "vacancy-serp__vacancy-compensation"}) or
            card.find("div", {"data-qa": "vacancy-serp__vacancy-compensation"}) or
            card.find(class_=re.compile(r"salary|compensation"))
        )
        salary = salary_el.get_text(strip=True) if salary_el else "Зарплата не указана"
        salary = re.sub(r"\s+", " ", salary).strip()
        
        # City
        city_el = (
            card.find("div", {"data-qa": "vacancy-serp__vacancy-address"}) or
            card.find(class_=re.compile(r"address|location|city"))
        )
        city = city_el.get_text(strip=True) if city_el else "Астана"
        city = city.split(",")[0].strip()
        
        # Experience
        exp_el = (
            card.find("div", {"data-qa": "vacancy-serp__vacancy-work-experience"}) or
            card.find(class_=re.compile(r"experience"))
        )
        experience = exp_el.get_text(strip=True) if exp_el else "Не указан"
        
        # Date
        date_el = (
            card.find("span", {"data-qa": "vacancy-serp__vacancy-date"}) or
            card.find("div", class_=re.compile(r"date|time"))
        )
        date = date_el.get_text(strip=True) if date_el else "Недавно"
        
        # Short description
        desc_el = (
            card.find("div", {"data-qa": "vacancy-serp__vacancy_snippet_responsibility"}) or
            card.find("div", class_=re.compile(r"description|snippet|responsibilities"))
        )
        description = desc_el.get_text(strip=True) if desc_el else "Подробности на сайте hh.kz"
        
        return {
            "id": job_id,
            "title": title[:150],
            "company": company[:100],
            "salary": salary[:80],
            "city": city[:60],
            "experience": experience[:60],
            "date": date[:30],
            "description": description[:600],
            "url": url,
        }

    def get_vacancy_details(self, url: str) -> Optional[dict]:
        """Fetch full vacancy details from individual page."""
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            desc_el = soup.find("div", {"data-qa": "vacancy-description"})
            if desc_el:
                return {"full_description": desc_el.get_text(strip=True)[:2000]}
        except Exception as e:
            logger.error(f"Detail fetch error: {e}")
        return None
