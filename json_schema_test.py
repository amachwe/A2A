import jsonschema
import json
import hypothesis_jsonschema


from gen_ai_web_server import llm_client

manual_example = {
    "type": "text",
    "text": "This is some example text.",
    "metadata": {
      "author": "John Doe",
      "date": "2024-10-27"
    }
  }
manual_schema = {
        "properties": {
          "type": {
            "const": "text",
            "default": "text",
            "description": "Type of the part",
            "examples": [
              "text"
            ],
            "title": "Type",
            "type": "string"
          },
          "text": {
            "title": "Text",
            "type": "string"
          },
          "metadata": {
            "anyOf": [
              {
                "additionalProperties": {},
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "default": "null",
            "title": "Metadata"
          }
        },
        "required": [
          "type",
          "text"
        ],
        "title": "TextPart",
        "type": "object"
      }

def validate(example, schema):
    jsonschema.validate(example, schema)
    



def get_refs_list(schema):
    """Get the list of references from the given schema def."""
    string = json.dumps(schema, indent=2)
    i = string.find("#",0)
    refs = []
    while i != -1:
        substr = string[i:]
        j = 0
        while j < len(substr) and substr[j] != '"':
            j+=1

        refs.append(substr[:j].split("/")[-1])
        i = string.find("#",i+j)

    return refs

def build_prompt(schema, def_name):
    """Build the prompt to generate the example from the schema."""
    return [{"role": "user", "content": f"The JSON schema is given below: {schema}\n. Generate a complete JSON example for the object {def_name} that is valid according to the schema, including the optional keys."}]

if __name__ == "__main__":

    import tqdm 
    import time

    BUILD = False

    client = llm_client.GeminiClient()

    # Extract the schema from the file and then the definitions from the schema.
    raw_schema = open("a2a.json",'r',encoding="utf-8").read()
    jschema = json.loads(raw_schema)
    defs = jschema['$defs']


    examples = {}

    if BUILD:

        for name, schema in tqdm.tqdm(defs.items()):

            # Optimisation 
            refs = get_refs_list(schema)
            str_schema = json.dumps(schema, indent=2)
            for ref in refs:
                str_schema += "\n" + json.dumps(defs[ref], indent=2)

            final_prompt = build_prompt(str_schema, name) 
            

            try:
                time.sleep(15)  # to avoid rate limit on free tier (Gemini).
                response = client.send_request(final_prompt)
                text_resp = client.extract_response(response)
                example = text_resp.split("```")[1][4:]
                examples[name] = json.loads(example)
                try:
                    jsonschema.validate(examples[name],defs[name])
                    print("Validation successful")
                except Exception as e:
                    print("Validation Error: ", repr(e))

            except Exception as e: 
                print("----")
                print("Error in generating example for schema: ", name)
                print("Response: ", example)
                print("Schema: ", text_resp)
                print("Error: ", repr(e))
                continue

        open("examples_a2a.json",'w',encoding="utf-8").write(json.dumps(examples, indent=2))
    else:
        # Test
        FILE = "examples_a2a.json"
        examples = json.loads(open(FILE,'r',encoding="utf-8").read())
        
        errors = []
        for name, example in tqdm.tqdm(examples.items()):
            try:
                print(name)
                validate(example, jschema)
            except Exception as e:
                errors.append(name)
                print("Validation Error: ", repr(e))
                print("Example: ", example)
                print("Schema: ", defs[name])
                print("")
                
                continue
          
  
        print("Errors: ", errors)
        print("Total number of errors: ", len(errors))




   

