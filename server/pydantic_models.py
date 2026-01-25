# here we will define the pydantic structure  of the project.. 
from langchain_core.messages import BaseMessage , AIMessage , HumanMessage , ToolMessage
from pydantic import BaseModel , Field , HttpUrl , FilePath
from typing import Optional , Literal
class feature1_6(BaseModel):
     user_id : str = Field(...,  description="user id is compulsary")
     chat_id : str = Field(..., description="chat id ")
     message : str = Field(description="Human message  for llm")
     
class pydantic_for_feature_1_chat_output(BaseModel):
    title : str = Field(..., description="Title of the answer" )
    body : str = Field(..., description="body of the answer if the it contains code enclose with <code> if conatins formula <formula>")
    links : list[HttpUrl] = Field(description="links from search tool")
    Need_of_manim : Literal["YES" , "No"] = Field("only yes if  you think manim animation is needed.")
    manim_video_path : Optional[str] = Field(description="the manim video path if availlable else return /path/demo.mp4")
    main_video_prompt : str = Field(description="proper propmt  for AI to generate manim animation, by mentioning all the required context (only when need of manim )")
    next_related_topic : list[str] = Field("related topics that student can explore any 2")
    next_questions : list[str] = Field(description="next possible related questions (any 2)")