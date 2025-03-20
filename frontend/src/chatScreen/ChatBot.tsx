// src/components/ChatBot.tsx

import React from 'react';
import axios from 'axios';
import { DeepChat } from "deep-chat-react";

let currentChatDetail: any = [];
let chatHistor_LLM: any = [];
let newRecord: any = {};
const ChatBot: React.FC = () => {
  
    const requestInterceptor = (request: { body: any }) => {
        newRecord = {};
        newRecord.questions = request.body["messages"][0].text;
        const currentMessages: any = {
          role: "user",
          html: request.body["messages"][0].text,
        };
        currentChatDetail.push(currentMessages);
        const currentMessages_LLM: any = {
          "role": "user",
          "content": request.body["messages"][0].text,
        };
        chatHistor_LLM.push(currentMessages_LLM);
        
        //Last 5 question and Answer in JSON Format
        const lastFiveMessages = chatHistor_LLM.slice(-10);
    
        request.body = {
          content: request.body["messages"][0].text,
          history:lastFiveMessages,
        };
        return request;
      };
      const responseInterceptor = (response: any) => {
        const formattedResponse = {
          html: response.text,
        };
        const currentMessages: any = {
          role: "ai",
          html: response.text,
        };
    
        // Add current messages to the message history
        currentChatDetail.push(currentMessages);
        const currentMessages_LLM: any = {
          "role": "assistant",
          "content": response.answer,
        };
    
        // Add current messages to the message history
        chatHistor_LLM.push(currentMessages_LLM);
    
        //const newRecord: any = {}; // Initialize as any to allow dynamic properties
        
        // {
        //   if(setData)
        //   setData("chatBot_New_FirstQuestion",newRecord.questions);
        // }
        // if (questions) newRecord.questions = question;
        newRecord.Answer = response.answer;
        newRecord.dateAndTime = new Date().toString();
        return formattedResponse;
      };
  return (
    <DeepChat
    connect={{
        url: `http://localhost:8000/api/chat`,
        additionalBodyProps: {},
      }}
      style={{
        borderRadius: "0px",
        width: "100%",
        // height:`${currentChatDetail.length==0?"72vh":"82vh"}`,
        height: "82vh",
      }}
      history={[{ role: 'bot', text: 'Hello! Type a message to start chatting about timesheets.' }]}
      requestInterceptor={requestInterceptor}
      responseInterceptor={responseInterceptor}
    />
  );
};

export default ChatBot;