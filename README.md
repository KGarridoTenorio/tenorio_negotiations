Otree Experiment

How to use? 

- Add your user_name to the Settings.py file under LOCAL_NAMES = ['glendronach', 'awesom-o-4000', 'Klauss-MacBook-Pro.local', 'Asus-Tuf-Dash-f15', 'mac.home']
- Use a Python environment > 11.9  
- Install packages in requirements.txt
- 1st install Ollama through https://ollama.com
- 2nd Check if ollama is active in your terminal through the command: "ollama run llama3" you can enter "/bye" and proceed...
- 3rd Paste this line of code in yout terminal to create each tailored LLM named "reader_of_offers": ollama create reader -f ./Ollama_LLMs/Modelfile_reader_of_offers
- ready to run the final magic command: otree devserver

The Buyer-Supplier negotiation set-up with full-information on counterpart constraints and supplier bearing the risk is inspired by Davis & Hyndman (2021). 
- Andrew M. Davis, Kyle Hyndman (2021) Private Information and Dynamic Bargaining in Supply Chains: An Experimental Study. Manufacturing & Service Operations Management 23(6):1449-1467. https://doi.org/10.1287/msom.2020.0896
