# Enhanced Reddit User Persona Script with Humor, Politics, and Topics (using Reddit JSON)
import requests
import re
import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from collections import Counter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame, Image
from reportlab.lib.units import inch

# Extract username from Reddit profile URL
def extract_username(profile_url):
    parsed = urlparse(profile_url)
    return parsed.path.strip("/").split("/")[-1]

# Fetch data from Reddit's public JSON endpoints
def fetch_user_data(username):
    headers = {"User-Agent": "PersonaScript/1.0 by u/OpenAI-Dev"}
    base = f"https://www.reddit.com/user/{username}"

    def fetch(url):
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                return res.json().get("data", {}).get("children", [])
            else:
                return []
        except:
            return []

    comments = fetch(f"{base}/comments.json?limit=100")
    posts = fetch(f"{base}/submitted.json?limit=100")

    def adapt(item):
        data = item.get("data", {})
        return {
            "text": data.get("body") or data.get("selftext") or data.get("title") or "",
            "link": f"https://www.reddit.com{data.get('permalink', '')}",
            "subreddit": data.get("subreddit", "unknown")
        }

    return [adapt(c) for c in comments], [adapt(p) for p in posts]

# Clean HTML
def clean_text(text):
    return BeautifulSoup(text or "", "html.parser").get_text()

# Simple sentiment estimation using positive/negative word lists
positive_words = {"love", "great", "excellent", "happy", "good", "fantastic", "amazing", "wonderful", "positive", "like"}
negative_words = {"hate", "terrible", "bad", "sad", "angry", "awful", "worst", "negative", "dislike", "pain"}

def estimate_sentiment(text):
    words = re.findall(r"\b\w+\b", text.lower())
    pos_count = sum(1 for w in words if w in positive_words)
    neg_count = sum(1 for w in words if w in negative_words)
    score = pos_count - neg_count
    return score

# Analyze text to build persona
def analyze_text(comments, posts):
    persona = {}
    citations = {}
    all_data = comments + posts

    if not all_data:
        return {"Note": "No public data available."}, {}

    # Interests
    subreddit_counts = Counter(d["subreddit"] for d in all_data)
    top_subs = subreddit_counts.most_common(5)
    persona["Interests"] = ", ".join(sr for sr, _ in top_subs) if top_subs else "Unknown"
    citations["Interests"] = [f"https://www.reddit.com/r/{sr}" for sr, _ in top_subs]

    # Sentiment / Tone
    scores = [estimate_sentiment(clean_text(d["text"])) for d in all_data if d["text"]]
    avg_sent = sum(scores) / len(scores) if scores else 0
    if avg_sent > 1:
        tone = "Positive"
    elif avg_sent < -1:
        tone = "Negative"
    else:
        tone = "Neutral"
    persona["Tone"] = tone
    citations["Tone"] = [d["link"] for d in all_data[:3]]

    # Writing Style
    slang_words = ["lol", "lmao", "dude", "bro", "/s", "haha"]
    has_slang = any(any(slang in d["text"].lower() for slang in slang_words) for d in all_data)
    long_words = [w for d in all_data for w in d["text"].split() if len(w) > 10]
    total_words = sum(len(d["text"].split()) for d in all_data if d["text"])
    if has_slang:
        style = "Informal"
    elif total_words and len(long_words) / total_words > 0.05:
        style = "Formal"
    else:
        style = "Neutral"
    persona["Writing Style"] = style
    citations["Writing Style"] = [d["link"] for d in all_data[:3]]

    # Humor Type
    if any("/s" in d["text"] or "sarcasm" in d["text"].lower() for d in all_data):
        persona["Humor Type"] = "Sarcastic / Ironic"
        citations["Humor Type"] = [d["link"] for d in all_data if "/s" in d["text"]][:3]
    elif any(emoji in d["text"] for d in all_data for emoji in [":)", ":D", "😂"]):
        persona["Humor Type"] = "Light, Emoji-Driven"
        citations["Humor Type"] = [d["link"] for d in all_data if any(e in d["text"] for e in [":)", ":D", "😂"] )][:3]

    # Political Views
    politics_keywords = {
        "Left-leaning": ["socialist", "liberal", "woke", "progressive", "democrat"],
        "Right-leaning": ["conservative", "republican", "capitalist", "anti-woke", "right-wing", "freedom"]
    }
    for leaning, keywords in politics_keywords.items():
        for d in all_data:
            if any(k in d["text"].lower() for k in keywords):
                persona["Political Views"] = leaning
                citations["Political Views"] = [d["link"] for d in all_data if any(k in d["text"].lower() for k in keywords)][:3]
                break
        if "Political Views" in persona:
            break

    # Favorite Topics (frequent words), excluding common stopwords
    stopwords = {
        "the", "this", "that", "there", "have", "need", "only", "well", "just", "very", "will", "with", "from",
        "about", "which", "would", "what", "when", "were", "been", "they", "their", "your", "you", "our", "more", "some",
        "into", "could", "should", "them", "then", "than", "over", "those", "these", "here", "also", "because", "while",
        "each", "every", "even", "many", "most", "much", "being", "still", "such", "where", "who", "whom", "why", "how",
        "does", "did", "doing", "had", "has", "his", "her", "him", "she", "he", "its", "it's", "was", "are", "am", "is", "and", "or", "as", "at", "on", "in", "to", "an", "a", "of", "for", "by", "be", "if", "but", "not", "no", "yes"
    }
    words = [w.lower() for d in all_data for w in re.findall(r"\b\w+\b", d["text"]) if len(w) > 3 and w.lower() not in stopwords]
    common = Counter(words).most_common(10)
    persona["Top Words"] = ", ".join(w for w, _ in common) if common else "N/A"
    citations["Top Words"] = [d["link"] for d in all_data[:3]]

    return persona, citations

# Write persona to file
def write_persona(username, persona, citations):
    filename = f"persona_{username}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"Reddit User Persona for u/{username}\n")
        f.write("=" * 40 + "\n\n")
        for trait, value in persona.items():
            f.write(f"{trait}: {value}\n")
            if trait in citations:
                for cite in citations[trait]:
                    f.write(f"    - Source: {cite}\n")
            f.write("\n")
    print(f"Persona written to: {filename}")

# Write persona to PDF (new function)
def write_persona_pdf(username, persona, citations):
    filename = f"persona_{username}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    # Header Section (with placeholders for missing info)
    name = username.replace('_', ' ').title()
    age = "N/A"
    occupation = "N/A"
    status = "N/A"
    location = "N/A"
    tier = "N/A"
    archetype = "N/A"

    # You can try to infer some of these from posts, but for now, placeholders
    header_data = [
        [f'<b>{name}</b>', ''],
        ["AGE", age],
        ["OCCUPATION", occupation],
        ["STATUS", status],
        ["LOCATION", location],
        ["TIER", tier],
        ["ARCHETYPE", archetype],
    ]
    header_table = Table(header_data, colWidths=[2.5*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.whitesmoke),
        ('TEXTCOLOR', (0,0), (1,0), colors.darkorange),
        ('FONTNAME', (0,0), (1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (1,0), 18),
        ('BOTTOMPADDING', (0,0), (1,0), 12),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (1,0), 1, colors.orange),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.2*inch))

    # Motivations (Interests)
    story.append(Paragraph('<b>MOTIVATIONS</b>', styles['Heading3']))
    motivations = persona.get("Interests", "N/A")
    story.append(Paragraph(motivations, styles['Normal']))
    story.append(Spacer(1, 0.15*inch))

    # Personality (Tone, Writing Style)
    story.append(Paragraph('<b>PERSONALITY</b>', styles['Heading3']))
    tone = persona.get("Tone", "N/A")
    style = persona.get("Writing Style", "N/A")
    personality_text = f"Tone: {tone}<br/>Writing Style: {style}"
    story.append(Paragraph(personality_text, styles['Normal']))
    story.append(Spacer(1, 0.15*inch))

    # Behaviour & Habits (from posts/comments, generic for now)
    story.append(Paragraph('<b>BEHAVIOUR & HABITS</b>', styles['Heading3']))
    habits = [
        "Active on Reddit, engages in discussions.",
        "Prefers certain subreddits: " + persona.get("Interests", "N/A"),
        f"Writing style is {style.lower()}.",
        f"General tone is {tone.lower()}.",
        "Posts and comments regularly."
    ]
    for h in habits:
        story.append(Paragraph(f"• {h}", styles['Normal']))
    story.append(Spacer(1, 0.15*inch))

    # Frustrations (generic, as not available from Reddit)
    story.append(Paragraph('<b>FRUSTRATIONS</b>', styles['Heading3']))
    frusts = [
        "May encounter toxic discussions.",
        "Sometimes lacks context in threads.",
        "Difficulty finding high-quality content.",
        "Occasional negative interactions."
    ]
    for f in frusts:
        story.append(Paragraph(f"• {f}", styles['Normal']))
    story.append(Spacer(1, 0.15*inch))

    # Goals & Needs (generic, as not available from Reddit)
    story.append(Paragraph('<b>GOALS & NEEDS</b>', styles['Heading3']))
    goals = [
        "To find interesting content and discussions.",
        "To connect with like-minded individuals.",
        "To express opinions and share knowledge.",
        "To enjoy a positive online experience."
    ]
    for g in goals:
        story.append(Paragraph(f"• {g}", styles['Normal']))
    story.append(Spacer(1, 0.15*inch))

    # Humor Type
    if "Humor Type" in persona:
        story.append(Paragraph('<b>HUMOR TYPE</b>', styles['Heading3']))
        story.append(Paragraph(persona["Humor Type"], styles['Normal']))
        story.append(Spacer(1, 0.15*inch))

    # Political Views
    if "Political Views" in persona:
        story.append(Paragraph('<b>POLITICAL VIEWS</b>', styles['Heading3']))
        story.append(Paragraph(persona["Political Views"], styles['Normal']))
        story.append(Spacer(1, 0.15*inch))

    # Top Words (Favorite Topics)
    if "Top Words" in persona:
        story.append(Paragraph('<b>FAVORITE TOPICS</b>', styles['Heading3']))
        story.append(Paragraph(persona["Top Words"], styles['Normal']))
        story.append(Spacer(1, 0.15*inch))

    # Highlighted Quote (from a random post/comment, or generic)
    quote = None
    if citations.get("Interests"):
        quote = f"\"I enjoy participating in {persona.get('Interests', 'various topics')} discussions on Reddit.\""
    else:
        quote = "\"I want to spend less time searching and more time enjoying my Reddit experience.\""
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f'<font color="orange"><b>{quote}</b></font>', styles['Title']))

    doc.build(story)
    print(f"Persona PDF written to: {filename}")

# Main loop
def main():
    print("Reddit User Persona Builder")
    print("-" * 30)
    # ASK FOR URL interactively
    try:
        url = input("Enter a Reddit profile URL- ").strip()
    except EOFError:
        print("Input not supported in this environment. Please hardcode the URL.")
        return
    username = extract_username(url)
    if not username:
        print("Invalid URL.")
        return
    print(f"Fetching data for u/{username}...")
    comments, posts = fetch_user_data(username)
    print(f"Fetched {len(comments)} comments and {len(posts)} posts.")
    persona, citations = analyze_text(comments, posts)
    write_persona_pdf(username, persona, citations)

if __name__ == "__main__":
    main()
