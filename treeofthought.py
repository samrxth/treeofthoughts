import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
from assist import remove_outlier

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(api_key=openai_api_key, model="gpt-4o", temperature=0.7)
llmforscore = ChatOpenAI(api_key=openai_api_key, model="gpt-4o", temperature=1.5)

thought_prompt = PromptTemplate(
    input_variables=["headline", "article"],
    template="""
    Headline: {headline}
    Article: {article}
    do not generate any formatting or headings, simply give a list of thoughts in a list
    Generate the top 5 initial thoughts based on the news article. Do not generate a very optimistic thought for a solely negative article
    """,
)

branch_prompt = PromptTemplate(
    input_variables=["thought"],
    template="""
    Thought: {thought}
    Generate further insights and explanations for this thought.
    do not generate any formatting or headings, simply give a flat list of unformatted insights
    do not refrain from generating strongly negative or strongly positive insights if they seem fitting
    correct type of answer:
    - insight 1
    - insight 2
    - insight 3
    - insight 4
    """,
)

score_prompt = PromptTemplate(
    input_variables=["thought", "explanation"],
    template="""
    Thought: {thought}
    Explanation: {explanation}
    Evaluate the explanation and generate a numeric score for its impact on the stock market based on the following scale:
    - Highly Positive: 0.7 to 1
    - Positive: 0.5 to 0.699
    - Neutral Positive: 0.1 to 0.499
    - Neutral: -0.1 to 0.1 
    - Neutral Negative: -0.499 to -0.1
    - Negative: -0.5 to -0.699
    - Highly Negative: -0.7 to -1
    The scores should follow a normal distribution similar to the bell curve, with significant deviations from the center. Ensure the values have three significant figures. Avoid clustering scores too closely around the center.
    you need to be more confident, do not rely on 0.4-0.7 be bold, be strong and think. don't fall into repetition
    don't be afraid to be strongly negative or positive, or even strongly neutral
    Only provide the numeric score with no other characters except the sign, period, and integers that make the number.
    
    Shot 1:
    Thought: Nvidia is generating excitement with its focus on AI advancements at the upcoming GTC.
    Explanation 1: Nvidia's continued leadership in AI could significantly enhance its market position, making it an attractive option for investors looking for growth in cutting-edge technology sectors.
    Score: +0.967
    Explanation 2: The anticipation of new AI products is expected to boost investor enthusiasm and could lead to a notable increase in Nvidia’s stock price as the market reacts to the potential for groundbreaking innovations.
    Score: +0.894

    Shot 2:
    Thought: META is grappling with heightened scrutiny over its data handling and privacy practices.
    Explanation 1: Increased regulatory scrutiny could result in stringent compliance costs and restrictions, possibly chilling investor sentiment due to fears of decreased operational flexibility.
    Score: -0.753
    Explanation 2: Persistent privacy concerns might lead to reduced user engagement, impacting ad revenues and posing a substantial threat to META's core business model.
    Score: -0.817

    Shot 3:
    Thought: Laser Photonics Corporate is making steady progress in its operational strategies without disrupting the market.
    Explanation 1: The company’s consistent and strategic updates may reassure existing investors of stability but are unlikely to draw significant new investment in the short term.
    Score: +0.143
    Explanation 2: While operational updates are positive, they do not significantly shift the market dynamics or impact the stock price in a major way, leading to a minimal change in investor perception.
    Score: +0.057
    """,
)

thought_chain = LLMChain(llm=llm, prompt=thought_prompt)
branch_chain = LLMChain(llm=llm, prompt=branch_prompt)
score_chain = LLMChain(llm=llmforscore, prompt=score_prompt)

def generate_thoughts(headline, article):
    response = thought_chain.invoke({"headline": headline, "article": article})
    try:
        thoughts = response['text'].strip().split('\n')
    except:
        try:
            thoughts = response.strip().split('\n')
        except:
            return []
    return [thought.strip() for thought in thoughts if thought.strip()]

def branch_out_thoughts(thought):
    response = branch_chain.invoke({"thought": thought})
    try:
        branches = response['text'].strip().split('\n')
    except:
        try:
            branches = response.strip().split('\n')
        except:
            return []
    return [branch.strip() for branch in branches if branch.strip()]

def score_thought(thought, explanation):
    response = score_chain.invoke({"thought": thought, "explanation": explanation})
    try:
        score = response.strip()
    except:
        try:
            score = response['text'].strip()
        except:
            print(response)
            return []
    try:
        score = float(score)
    except ValueError:
        pass
    return score

def final_prediction(thoughts, branches, scores):
    print(scores)
    node_extremes=[]
    for score_arr in scores:
        for i in range(len(score_arr)):
            try:
                score_arr[i] = float(score_arr[i])
            except ValueError:
                try:
                    score_arr[i] = float(score_arr[i].split()[-1])
                except ValueError:
                    score_arr[i] = 0
        score_arr = [score for score in score_arr if score != 0]
        score_arr = remove_outlier(score_arr)
        if max(score_arr) > -min(score_arr):
            node_extremes.append(max(score_arr))
        else:
            node_extremes.append(min(score_arr))
    return sum(node_extremes)/len(node_extremes)
    # positive_scores = []
    # negative_scores = []
    # for score_list in scores:
    #     for score in score_list:
    #         try:
    #             score = float(score)
    #         except ValueError:
    #             continue
    #         if score > 0:
    #             positive_scores.append(score)
    #         elif score < 0:
    #             negative_scores.append(score)
    # 
    # print("scores: ", scores)
    # print("positive_scores: ", positive_scores)
    # print("negative_scores: ", negative_scores)
    #
    # if (len(positive_scores) - len(negative_scores)) in range(-2,2):
    #     final_score = 0  # Conflicting insights
    # else:
    #     # note: may turn this into average of sublist and then average of the averages
    #     flat_scores = []
    #     for score_list in scores:
    #         if isinstance(score_list, list):
    #             for score in score_list:
    #                 try:
    #                     score = float(score)
    #                 except ValueError:
    #                     continue
    #                 flat_scores.append(score)
    #         elif isinstance(score_list, float):
    #             flat_scores.append(score_list)
    #
    #     final_score = sum(flat_scores) / len(flat_scores)
    #
    # return round(final_score, 3)

def ToT(headline, article):
    thoughts = generate_thoughts(headline, article)
    
    all_branches = []
    all_scores = []
    
    for thought in thoughts:
        branches = branch_out_thoughts(thought)
        all_branches.append(branches)
        
        scores = []
        for branch in branches:
            score = score_thought(thought, branch)
            scores.append(score)
        
        all_scores.append(scores)
    
    prediction = final_prediction(thoughts, all_branches, all_scores)
    print("ToT score:", prediction)
    
    return prediction
