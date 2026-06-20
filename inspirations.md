-see this astro js site ...try to keep the design somewhat like this 
https://www.mariannefeng.com/reading 


-check this https://github.com/RUCAIBox/RecBole , its your repo of reccomendation algorithms , find alternatives , implementations etc.


-look for langcache (https://redis.io/langcache/) for reducing api costs for over 90% , pair it up with pydantic aswell.
the api costs are for the 'fusion feature' of repos and components , that i will add later

-also avoid slop like ai chat bot etc..if i want i  could do a mermaid style thing to show interrelation


-the recommeended repos can be in this format
<img width="488" height="724" alt="image" src="https://github.com/user-attachments/assets/7b2f021f-675e-433b-928b-e04682cca42b" /> 
pokemon stats like feature cards in view.
metadata , implmentations and high level overview of that repo



- ##Spotify's new approach towards rec sys
    https://www.youtube.com/watch?v=5YSJEP0HWzM&list=PLcfpQ4tk2k0UMEJY1KzWu02OkvCc1e5og

notes below 
- <img width="2880" height="1800" alt="image" src="https://github.com/user-attachments/assets/a800ac60-d81f-4dc5-b3f9-64a19e3eee79" />

<img width="1080" height="608" alt="image" src="https://github.com/user-attachments/assets/c24c0670-7292-41a6-8fe3-5b3b4e80cdc2" />

<img width="1924" height="1218" alt="image" src="https://github.com/user-attachments/assets/a0b40713-2ed4-420d-b7cd-5ad4a5017205" />
uses an autoencoder (this was the old approach for generalised user representations...this was in 2024)





<img width="1112" height="626" alt="image" src="https://github.com/user-attachments/assets/3dd630ed-eaa1-4305-ba26-c3a237f2ac67" />
this ones the newer approach
context engineering is crucial here




<img width="1100" height="622" alt="image" src="https://github.com/user-attachments/assets/23e98b28-3467-40eb-ad01-bcc6cd955940" />
cross content modeling
embed users , tracks , items together in the embed space.
imp: this helps you navigate whats close to you , whats not close to you and helps you navigate the space


<img width="954" height="604" alt="image" src="https://github.com/user-attachments/assets/31c70454-c0fd-43b8-aef1-acd28912c780" />
feeding content and user vectors to a fine tuned LLM(small open source models) to recieve sequenced rec



<img width="1100" height="602" alt="image" src="https://github.com/user-attachments/assets/15602f40-5173-4a23-aaf8-36a9bd10551a" />
how do you teach the llms about the content
use a concept called 
'Semantic ID"
so itss:
-take a vector that represents a track/music
-tokenize it
-compress the thousand dimension vector to 4 or 6 tokens
-and then use the tokens to train the LLM
-that helps the LLM to autoregressively generate the next token(in case of spotify , the next token is a song)

they are countinually training, post training  these llms.


<img width="1108" height="616" alt="image" src="https://github.com/user-attachments/assets/78ca424a-7f3a-42cb-b032-c7eec00e350f" />

<img width="1032" height="482" alt="image" src="https://github.com/user-attachments/assets/55b49da1-bb30-408d-b1d0-36b6a5dc49cf" />




<img width="986" height="234" alt="image" src="https://github.com/user-attachments/assets/aaed2c3a-4a83-466f-b75b-ff1f9566b33f" />
about spotify's new features like 
1) taste profile (basically like a system prompt about your tastes)
   *note that they dont have sandbox to this like a 'project' thing in qwen.
   i should be able to create the different enviornments for different projects and tastes


<img width="1000" height="502" alt="image" src="https://github.com/user-attachments/assets/a1edec6a-2a7c-4324-a129-fd6b9f5c544b" />


<img width="1034" height="510" alt="image" src="https://github.com/user-attachments/assets/fde46b6a-5386-49a7-9926-957e5de2c6c8" />
<img width="1044" height="358" alt="image" src="https://github.com/user-attachments/assets/c751b8d1-4a09-4415-a652-a3b2f102e96b" />

small token budget of llms , so thats why you need to keep long term user representations ,and should be lightweight


*note : i can use some kind of smart compression to boil down user's long term representation and history to feed the LLM's prompt
some algorithm like ZSTD /LZ4 etc (or find more sprecialisalsed algorithms for this purpouse .....dont try to make an end to end product with this , for experimentation first fork down a repo that is similar to this and implement the heavy compression tests for now)


 <img width="1086" height="584" alt="image" src="https://github.com/user-attachments/assets/69446d83-6a58-40dc-b873-326d8aaa3bb8" />
  this is purely for next episode recommendation , not recommendation in discovery 

  the next episode recommendation is based on 2M dataset /episode interactions

the specifications are listed above , go through them once and find alternatives for what you can do 


<img width="964" height="432" alt="image" src="https://github.com/user-attachments/assets/e727264b-f7ef-41fd-94ce-a7ffbe62f226" />
dont replace the trad recs , just make sure you add the new approaches wherever it is feasible.
moving from trad rec to sequential modelling


read more about sequential modelling 
