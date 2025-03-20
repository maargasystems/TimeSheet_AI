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
        
        // Last 5 question and Answer in JSON Format
        const lastFiveMessages = chatHistor_LLM.slice(-10);
    
        request.body = {
          question: request.body["messages"][0].text,
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
    
        newRecord.Answer = response.answer;
        newRecord.dateAndTime = new Date().toString();
        return formattedResponse;
      };

  return (
    <DeepChat
    connect={{
      url: `http://localhost:8000/timesheetanalyze`,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    }}
      style={{
        borderRadius: "0px",
        width: "100%",
        height: "82vh",
      }}
      history={[{ role: 'bot', text: 'Hello! Type a message to start chatting about timesheets.' }]}
      requestInterceptor={requestInterceptor}
      responseInterceptor={responseInterceptor}
    />
  );
};

export default ChatBot;